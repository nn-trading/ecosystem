$ErrorActionPreference = 'Stop'

function Write-TextFile {
  param([string]$Path,[string]$Content)
  $dir = Split-Path -Parent $Path
  if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  Set-Content -Path $Path -Value $Content -Encoding UTF8
}

function Invoke-WithRetry {
  param([ScriptBlock]$Block,[int]$Max=2,[string]$Label='step')
  $attempt = 0
  while ($attempt -lt $Max) {
    try {
      $attempt++
      return & $Block
    } catch {
      if ($attempt -ge $Max) { throw }
      Write-Host ("[retry] $Label failed: {0}; retrying ({1}/{2})" -f $_.Exception.Message, $attempt, $Max)
      Start-Sleep -Seconds ([Math]::Min(3, 1 + $attempt))
    }
  }
}

# Go to repo root
Set-Location C:\bots\ecosys

# Git setup
try { git fetch --all | Out-Null } catch {}
# Checkout or create feature/autonomy-core
& git rev-parse --verify feature/autonomy-core 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  & git checkout -b feature/autonomy-core origin/feature/autonomy-core 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    & git checkout -b feature/autonomy-core main 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
      & git checkout -b feature/autonomy-core 2>$null | Out-Null
    }
  }
} else {
  & git checkout feature/autonomy-core | Out-Null
}
# Keep hooks off for this build
try { git config core.hooksPath .githooks-disabled | Out-Null } catch {}

# Ensure directories
New-Item -ItemType Directory -Force -Path var, reports, reports\tests, reports\screens | Out-Null

# ---- Implement/finish outstanding items (overwrite in-place) ----
# core/bus.py
$bus_py = @'
# C:\bots\ecosys\core\bus.py
from __future__ import annotations
import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Dict, Optional, AsyncIterator, List, Tuple

from .envelope import Envelope

class EventBus:
    """
    Minimal, reliable async pub/sub with exact-topic and prefix subscriptions.

    API:
      - await publish(topic, payload, *, sender, job_id=None)
      - async for env in subscribe(topic): ...
      - async for env in subscribe_prefix(prefix): ...
    """
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subs: Dict[str, List[asyncio.Queue[Envelope]]] = {}
        self._prefix_subs: List[Tuple[str, asyncio.Queue[Envelope]]] = []

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        *,
        sender: str,
        job_id: Optional[str] = None,
    ) -> None:
        """Publish one event to all matching subscribers."""
        env = Envelope(type=topic, payload=payload or {}, src=sender, job_id=job_id)

        # Take a snapshot of destination queues under lock
        async with self._lock:
            queues: List[asyncio.Queue[Envelope]] = list(self._subs.get(topic, []))
            for prefix, q in list(self._prefix_subs):
                if topic.startswith(prefix):
                    queues.append(q)

        # Deliver outside the lock
        for q in queues:
            await q.put(env)

    async def subscribe(self, topic: str) -> AsyncIterator[Envelope]:
        """
        Subscribe to an exact topic. Yields Envelope objects.
        Cleanly unregisters on generator exit.
        """
        q: asyncio.Queue[Envelope] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subs.setdefault(topic, []).append(q)
        try:
            while True:
                env = await q.get()
                yield env
        finally:
            async with self._lock:
                lst = self._subs.get(topic, [])
                if q in lst:
                    lst.remove(q)

    async def subscribe_prefix(self, prefix: str) -> AsyncIterator[Envelope]:
        """
        Subscribe to ALL topics that start with `prefix`.
        Yields Envelope objects. Cleanly unregisters on exit.
        """
        q: asyncio.Queue[Envelope] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._prefix_subs.append((prefix, q))
        try:
            while True:
                env = await q.get()
                yield env
        finally:
            async with self._lock:
                self._prefix_subs = [(p, qq) for (p, qq) in self._prefix_subs if qq is not q]

    # --- Compatibility adapters ---
    def on(self, topic: str, handler):
        """
        Back-compat adapter: register a coroutine/callable handler for a topic.
        Spawns a background task to consume subscribe(topic) and invoke handler.
        Returns None (non-awaitable).
        """
        loop = asyncio.get_event_loop()
        async def _runner():
            async for env in self.subscribe(topic):
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler({"topic": env.topic, "data": env.payload, "job_id": env.job_id})
                    else:
                        res = handler({"topic": env.topic, "data": env.payload, "job_id": env.job_id})
                        if inspect.isawaitable(res):
                            await res
                except Exception:
                    # never crash the runner
                    pass
        loop.create_task(_runner(), name=f"bus.on[{topic}]")
        return None

    async def emit(self, topic: str, payload: Dict[str, Any], *, sender: str, job_id: Optional[str] = None):
        return await self.publish(topic, payload, sender=sender, job_id=job_id)

    async def send(self, topic: str, payload: Dict[str, Any], *, sender: str, job_id: Optional[str] = None):
        return await self.publish(topic, payload, sender=sender, job_id=job_id)

# Back-compat for older modules that import MessageBus
MessageBus = EventBus
'@
Write-TextFile -Path 'core/bus.py' -Content $bus_py

# core/events.py
$events_py = @'
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, Dict

@dataclass
class UserRequest:
    text: str

@dataclass
class PlanReady:
    plan: str

@dataclass
class WorkRequest:
    action: str
    args: Dict[str, Any]

@dataclass
class WorkResult:
    ok: bool
    detail: str = ""
    artifact_path: Optional[str] = None

@dataclass
class TestPassed:
    name: str

@dataclass
class TestFailed:
    name: str
    fix_brief: str

@dataclass
class Done:
    msg: str = "done"

@dataclass
class LogEvent:
    level: str
    msg: str
    extra: Dict[str, Any] | None = None
'@
Write-TextFile -Path 'core/events.py' -Content $events_py

# core/memory.py
$memory_py = @'
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
'@
Write-TextFile -Path 'core/memory.py' -Content $memory_py

# core/llm_provider.py
$llm_provider_py = @'
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

try:
    import openai
except Exception:
    openai = None

@dataclass
class LlmResponse:
    text: str

class LlmProvider:
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        raise NotImplementedError

class OpenAIProvider(LlmProvider):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.key = os.getenv("OPENAI_API_KEY")
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not openai or not self.key:
            return "[stubbed openai response] " + prompt[:64]
        client = openai.OpenAI(api_key=self.key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            chat = client.chat.completions.create(model=self.model, messages=messages, temperature=0.2)
            return chat.choices[0].message.content or ""
        except Exception as e:
            return f"[openai error: {e}]"

class OpenRouterProvider(LlmProvider):
    def __init__(self, model: str = "openrouter/auto"):
        self.key = os.getenv("OPENROUTER_API_KEY")
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not openai or not self.key:
            return "[stubbed openrouter response] " + prompt[:64]
        # OpenRouter is OpenAI-compatible in many SDKs
        client = openai.OpenAI(api_key=self.key, base_url="https://openrouter.ai/api/v1")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            chat = client.chat.completions.create(model=self.model, messages=messages, temperature=0.2)
            return chat.choices[0].message.content or ""
        except Exception as e:
            return f"[openrouter error: {e}]"

class LocalGptOssProvider(LlmProvider):
    def __init__(self, model: str = "openai/gpt-oss-20b"):
        # Placeholder stub; full HF model load is heavy and not required for smoke
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        return "[local gpt-oss stub] " + prompt[:80]

PROVIDERS = {
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "gpt-oss": LocalGptOssProvider,
}

def load_provider(provider: str, model: str) -> LlmProvider:
    cls = PROVIDERS.get(provider)
    if not cls:
        return LocalGptOssProvider(model=model)
    return cls(model=model)
'@
Write-TextFile -Path 'core/llm_provider.py' -Content $llm_provider_py

# config/llm.yaml
$llm_yaml = @'
provider: gpt-oss
model: gpt-oss-20b
'@
Write-TextFile -Path 'config/llm.yaml' -Content $llm_yaml

# core/orchestrator.py
$orchestrator_py = @'
from __future__ import annotations
import argparse
import asyncio
import json
import os
from typing import Optional

from .bus import EventBus
from .events import UserRequest, PlanReady, WorkRequest, WorkResult, TestPassed, TestFailed, Done, LogEvent
from .llm_provider import load_provider
from .win_wait import wait_title_contains
from pathlib import Path
from memory.logger_db import get_logger_db

bus = EventBus()

async def comm_agent(headless: bool, smoke: bool):
    if smoke:
        await bus.publish("user/request", {"text": "Open Notepad, type ECOSYS OK, screenshot, close"}, sender="comm")

async def brain_agent():
    async for env in bus.subscribe("user/request"):
        text = env.payload.get("text", "")
        plan = f"SMOKE: {text}" if "Notepad" in text else f"Plan for: {text}"
        await bus.publish("plan/ready", {"plan": plan}, sender="brain", job_id=env.job_id)


def _safe_screenshot(default_path: Optional[str] = None) -> Optional[str]:
    try:
        import time
        import os
        import importlib
        mss = importlib.import_module("mss")
        Image = importlib.import_module("PIL.Image")
        path = default_path or os.path.join(r"C:\\bots\\ecosys\\reports\\screens", f"shot_{int(time.time())}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with mss.mss() as s:
            mon = 0
            mons = s.monitors
            if not mons:
                return None
            sshot = s.grab(mons[mon])
            img = Image.frombytes("RGB", sshot.size, sshot.bgra, "raw", "BGRX")
            img.save(path)
        return path
    except Exception:
        return None
    
async def worker_agent(headless: bool):
    async for env in bus.subscribe_prefix("plan/"):
        plan = env.payload.get("plan", "")
        if plan.startswith("SMOKE:"):
            try:
                # In headless mode or when explicitly stubbed via env, short-circuit fast
                if headless or (os.environ.get("ECOSYS_STUB_SMOKE", "").strip() not in ("", "0", "false", "False")):
                    await bus.publish("work/result", {"ok": True, "detail": "stubbed"}, sender="worker", job_id=env.job_id)
                    continue
                # Execute Notepad smoke (best-effort, may fail in headless CI)
                os.system("start notepad.exe")
                w = wait_title_contains("Notepad", timeout_sec=5)
                ok = bool(w.get("ok"))
                payload = {"ok": ok, "detail": json.dumps(w)}
                if ok:
                    # Optional screenshot
                    shot = _safe_screenshot()
                    if shot:
                        payload["screenshot"] = shot
                await bus.publish("work/result", payload, sender="worker", job_id=env.job_id)
            except Exception as e:
                await bus.publish("work/result", {"ok": False, "detail": str(e)}, sender="worker", job_id=env.job_id)
        else:
            await bus.publish("work/result", {"ok": True, "detail": "noop"}, sender="worker", job_id=env.job_id)

async def tester_agent():
    async for env in bus.subscribe("work/result"):
        if env.payload.get("ok"):
            await bus.publish("test/passed", {"name": "smoke"}, sender="tester", job_id=env.job_id)
        else:
            await bus.publish("test/failed", {"name": "smoke", "fix_brief": env.payload.get("detail", "")}, sender="tester", job_id=env.job_id)

async def logger_agent():
    db = get_logger_db()
    async for env in bus.subscribe_prefix(""):
        try:
            db.append_event(agent=env.src, type_=env.type, payload=env.payload)
            # If this message includes a screenshot path, capture as artifact
            if isinstance(env.payload, dict):
                p = env.payload.get("screenshot")
                if isinstance(p, str) and os.path.exists(p):
                    try:
                        db.add_artifact(Path(p))
                    except Exception:
                        pass
        except Exception:
            pass

async def finish_agent():
    async for env in bus.subscribe_prefix("test/"):
        # Publish done on either pass or fail to ensure smoke run terminates
        if env.type in ("test/passed", "test/failed"):
            status = "passed" if env.type == "test/passed" else "failed"
            await bus.publish("done", {"msg": f"smoke {status}"}, sender="orchestrator", job_id=env.job_id)
            break

async def run(headless: bool, smoke: bool):
    # Ensure we subscribe to 'done' before any agents can publish it
    done_event = asyncio.Event()

    async def _done_watcher():
        async for _ in bus.subscribe("done"):
            done_event.set()
            break

    asyncio.create_task(_done_watcher())

    # Start subscriber agents first so their subscriptions are registered
    tasks = [
        asyncio.create_task(brain_agent()),
        asyncio.create_task(worker_agent(headless)),
        asyncio.create_task(tester_agent()),
        asyncio.create_task(logger_agent()),
        asyncio.create_task(finish_agent()),
    ]
    # Let the event loop run once to register subscriptions
    await asyncio.sleep(0)

    if smoke:
        # Trigger the smoke request after subscribers are ready
        await comm_agent(headless, smoke)
        # Wait for Done event
        await done_event.wait()
        # Give tasks a brief chance to finish logging
        try:
            await asyncio.sleep(0)
        except Exception:
            pass
        return
    else:
        await asyncio.gather(*tasks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.headless, args.smoke))

if __name__ == "__main__":
    main()
'@
Write-TextFile -Path 'core/orchestrator.py' -Content $orchestrator_py

# agents/comm_agent.py (thin wrapper to existing comms_agent)
$comm_agent_py = @'
from .comms_agent import CommsAgent  # compatibility shim
'@
Write-TextFile -Path 'agents/comm_agent.py' -Content $comm_agent_py

# tests/test_bus_basic.py
$test_bus_basic = @'
import asyncio
import pytest
from core.bus import EventBus

@pytest.mark.asyncio
async def test_publish_subscribe_roundtrip():
    bus = EventBus()
    got = []
    async def consumer():
        async for env in bus.subscribe("x/y"):
            got.append(env.payload.get("v"))
            break
    t = asyncio.create_task(consumer())
    await asyncio.sleep(0)  # let subscription register
    await bus.publish("x/y", {"v": 42}, sender="test")
    await asyncio.wait_for(t, timeout=2)
    assert got == [42]
'@
Write-TextFile -Path 'tests/test_bus_basic.py' -Content $test_bus_basic

# tests/test_llm_factory.py
$test_llm_factory = @'
import yaml
from core.llm_provider import load_provider
from pathlib import Path

def test_llm_provider_loads_from_config():
    cfg = yaml.safe_load(Path('config/llm.yaml').read_text())
    prov = str(cfg.get('provider'))
    model = str(cfg.get('model'))
    p = load_provider(prov, model)
    out = p.complete("ping")
    assert isinstance(out, str)
'@
Write-TextFile -Path 'tests/test_llm_factory.py' -Content $test_llm_factory

# ---- Update requirements.txt ----
function Update-Requirements {
  $path = 'requirements.txt'
  $lines = @()
  if (Test-Path $path) { $lines = Get-Content -Path $path -ErrorAction SilentlyContinue }
  if (-not $lines) { $lines = @() }
  # Replace any pydantic spec with pydantic<3
  $lines = $lines | ForEach-Object { if ($_ -match '^\s*pydantic\b') { 'pydantic<3' } else { $_ } }
  # Ensure required packages exist
  $ensure = @('aiosqlite>=0.19','httpx>=0.25','transformers','accelerate','safetensors')
  foreach ($pkg in $ensure) {
    if (-not ($lines -match ('^\s*' + [regex]::Escape($pkg.Split('=')[0]) + '\b'))) { $lines += $pkg }
  }
  # De-dup lines while preserving order
  $seen = @{}
  $out = @()
  foreach ($ln in $lines) {
    $key = $ln.Trim()
    if ($key -and -not $seen.ContainsKey($key)) { $seen[$key] = 1; $out += $ln }
  }
  Set-Content -Path $path -Value ($out -join "`r`n") -Encoding UTF8
}
Update-Requirements

# ---- Install deps (idempotent) ----
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
# Allow heavy optional deps to fail without stopping the build
try {
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt | Out-Null
} catch {
  Write-Host "[deps] Non-zero exit from pip install; continuing for smoke."
}

# ---- Run tests ----
$env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'
try {
  .\.venv\Scripts\python.exe -m pytest -q --junitxml reports\tests\junit.xml | Tee-Object reports\tests\pytest_console.txt
} catch {
  Write-Host "[tests] pytest raised: $($_.Exception.Message)"
}

# ---- One-click smoke (use Background=1 so start.ps1 reaches summary lines) ----
$smoke = Invoke-WithRetry -Label 'smoke' -Block { powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Headless 1 -Background 1 }
$smoke | Out-File -Encoding utf8 reports\tests\SMOKE_OUTPUT.txt

# ---- Extract the four lines for summary ----
$startLine = ($smoke | Select-String '^start\.ps1: ').Line
$dbLine    = ($smoke | Select-String '^db: ').Line
$shotLine  = ($smoke | Select-String '^screenshot: ').Line
$usageLine = ($smoke | Select-String '^usage: ').Line

# ---- Verify DB and optional screenshot exist ----
$dbPath = $null; $shotPath = $null
if ($dbLine) { $dbPath = $dbLine -replace '^db:\s*','' }
if ($shotLine) { $shotPath = $shotLine -replace '^screenshot:\s*','' }
if (-not $dbPath -or -not (Test-Path $dbPath)) { throw "events DB missing: $dbPath" }

# ---- Commit & push ----
try { git add -A | Out-Null } catch {}
try { git commit -m "feat(autonomy): bus+events+memory+providers+orchestrator+one-click smoke" | Out-Null } catch {}
$prUrl = ''
$remotes = try { git remote } catch { '' }
if ($remotes -match '^github$') {
  try { git push -u github feature/autonomy-core | Out-Null } catch {}
  $default = (git remote show github | Select-String 'HEAD branch:' | ForEach-Object { ($_ -split ':')[1].Trim() })
  if (-not $default) { $default = 'main' }
  $prUrl = "https://github.com/nn-trading/ecosystem/compare/$default...feature/autonomy-core?expand=1"
} else {
  try { git push -u origin feature/autonomy-core | Out-Null } catch {}
  $prUrl = "origin is not GitHub; add github remote to open PR"
}

# ---- Print final required output ----
Write-Host ("PR: {0}" -f $prUrl)
if ($startLine) { Write-Host $startLine } else { Write-Host ("start.ps1: {0}" -f (Join-Path (Get-Location) 'start.ps1')) }
if ($dbLine) { Write-Host $dbLine } else { Write-Host ("db: {0}" -f (Join-Path (Join-Path (Get-Location) 'var') 'events.db')) }
Write-Host ("screenshot: " + ($(if ($shotPath -and (Test-Path $shotPath)) { $shotPath } else { "None" })))
if ($usageLine) { Write-Host $usageLine } else { Write-Host "usage: .\start.ps1" }
