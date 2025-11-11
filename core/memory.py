# C:\bots\ecosys\core\memory.py
from __future__ import annotations
import os, io, json, time, asyncio, tempfile, shutil, unicodedata
from core.ascii_writer import write_jsonl_ascii
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Iterable, List, Tuple

_ENV_ROOT = os.environ.get("ECOSYS_REPO_ROOT")
# Include broader set of Unicode separators/format characters
_WHITESPACE = " \t\r\n\f\v\u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000\ufeff\u200b\u2060"

def _clean_env_path(val: str) -> str:
    try:
        s = val.strip().strip('"').strip("'")
    except Exception:
        s = str(val)
    # Trim leading/trailing Unicode separators and control/format chars
    i, j = 0, len(s)
    def is_trim(ch: str) -> bool:
        cat = unicodedata.category(ch)
        return cat.startswith("Z") or cat.startswith("C")
    while i < j and is_trim(s[i]):
        i += 1
    while j > i and is_trim(s[j-1]):
        j -= 1
    return s[i:j]

if _ENV_ROOT:
    ROOT = os.path.abspath(_clean_env_path(_ENV_ROOT))
else:
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(ROOT, "workspace", "logs")
EVENTS_FILE = os.path.join(LOG_DIR, "events.jsonl")
SUMMARIES_FILE = os.path.join(LOG_DIR, "summaries.jsonl")

# Reasonable defaults; LoggerAgent can override via methods/params.
DEFAULT_KEEP_LAST = 50000  # keep this many recent events in the hot log file
TAIL_BLOCK = 64 * 1024     # bytes per backward read block

@dataclass
class EventRecord:
    ts: float
    topic: str
    sender: str
    job_id: Optional[str]
    payload: Dict[str, Any]

@dataclass
class SummaryRecord:
    ts: float
    range: Tuple[int, int]  # (start_line, end_line) summarized
    lines: int
    text: str

class Memory:
    """
    Persistent append-only JSONL event log with quick tail & safe rotation.
    - events.jsonl: every bus event, one JSON object per line.
    - summaries.jsonl: roll-up text for archived ranges (for fast cold-start recall).
    """
    def __init__(self, log_dir: Optional[str] = None):
        base = log_dir or LOG_DIR
        try:
            clean = base.strip().strip('"').strip("'")
        except Exception:
            clean = str(base)
        self.log_dir = os.path.normpath(clean)
        self.events_path = os.path.join(self.log_dir, "events.jsonl")
        self.summaries_path = os.path.join(self.log_dir, "summaries.jsonl")
        os.makedirs(self.log_dir, exist_ok=True)
        self._lock = asyncio.Lock()

    # ---------------- write ----------------

    async def append_event(self, topic: str, payload: Dict[str, Any], *, sender: str, job_id: Optional[str] = None) -> None:
        rec = EventRecord(ts=time.time(), topic=topic, sender=sender, job_id=job_id, payload=payload or {})
        await self._write_jsonl(self.events_path, asdict(rec))

    async def append_summary(self, text: str, *, start_line: int, end_line: int) -> None:
        rec = SummaryRecord(ts=time.time(), range=(start_line, end_line), lines=(end_line - start_line + 1), text=text)
        await self._write_jsonl(self.summaries_path, asdict(rec))

    async def _write_jsonl(self, path: str, obj: Dict[str, Any]) -> None:
        async with self._lock:
            write_jsonl_ascii(path, obj)

    # ---------------- read ----------------

    def count_lines(self, path: Optional[str] = None) -> int:
        path = path or self.events_path
        if not os.path.exists(path):
            return 0
        # Fast-ish: read in blocks and count '\n'
        n = 0
        with open(path, "rb") as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                n += b.count(b"\n")
        return n

    def tail_events(self, n: int) -> List[Dict[str, Any]]:
        """Return last n event records as dicts."""
        if not os.path.exists(self.events_path) or n <= 0:
            return []
        lines = self._tail_lines(self.events_path, n)
        out = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                # ignore broken lines
                pass
        return out

    def read_head(self, n: int) -> List[str]:
        if not os.path.exists(self.events_path) or n <= 0:
            return []
        out: List[str] = []
        with open(self.events_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, ln in enumerate(f, 1):
                out.append(ln)
                if i >= n:
                    break
        return out

    def _tail_lines(self, path: str, n: int) -> List[str]:
        """Read last n lines efficiently without loading the whole file."""
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            size = end
            buf = b""
            lines: List[bytes] = []
            while size > 0 and len(lines) <= n:
                step = min(TAIL_BLOCK, size)
                size -= step
                f.seek(size)
                chunk = f.read(step)
                buf = chunk + buf
                lines = buf.split(b"\n")
            # Take last n (drop possible trailing empty)
            if lines and lines[-1] == b"":
                lines = lines[:-1]
            tail = lines[-n:] if n < len(lines) else lines
            return [ln.decode("utf-8", errors="ignore") for ln in tail]

    # ---------------- rotation ----------------

    async def rotate_keep_last(self, keep_last: int = DEFAULT_KEEP_LAST) -> Tuple[int, int]:
        """
        Keep only the last `keep_last` lines in events.jsonl (atomically).
        Returns (old_count, new_count). No-op if already small.
        """
        # Fast path: avoid full line count for very large files or when MEM_ROTATE_FAST is truthy
        size = os.path.getsize(self.events_path) if os.path.exists(self.events_path) else 0
        fast_env = str(os.environ.get("MEM_ROTATE_FAST", "0")).strip().lower() not in ("0", "false", "no", "off")
        if size > 128 * 1024 * 1024 or fast_env:
            total = -1
        else:
            total = self.count_lines(self.events_path)
            if total <= keep_last:
                return (total, total)

        tail_lines = self._tail_lines(self.events_path, keep_last)
        async with self._lock:
            tmp_fd, tmp_path = tempfile.mkstemp(prefix="events_", suffix=".jsonl", dir=self.log_dir)
            os.close(tmp_fd)
            with open(tmp_path, "w", encoding="ascii", errors="ignore") as w:
                for ln in tail_lines:
                    w.write(ln if ln.endswith("\n") else ln + "\n")
            # atomic replace
            backup = self.events_path + ".bak"
            if os.path.exists(backup):
                try: os.remove(backup)
                except Exception: pass
            attempts = 0
            while True:
                try:
                    os.replace(self.events_path, backup)
                    break
                except PermissionError:
                    attempts += 1
                    if attempts >= 8:
                        raise
                    time.sleep(0.25 * attempts)
            os.replace(tmp_path, self.events_path)
            # best-effort cleanup backup
            try: os.remove(backup)
            except Exception: pass
        return (total, keep_last)

    # ---------------- convenience ----------------

    def stats(self) -> Dict[str, Any]:
        ev = self.count_lines(self.events_path)
        sm = self.count_lines(self.summaries_path)
        return {
            "events_file": self.events_path,
            "summaries_file": self.summaries_path,
            "events_lines": ev,
            "summaries": sm,
            "events_size_bytes": os.path.getsize(self.events_path) if os.path.exists(self.events_path) else 0,
            "summaries_size_bytes": os.path.getsize(self.summaries_path) if os.path.exists(self.summaries_path) else 0,
        }
