# C:\bots\ecosys\core\assistant_loader.py
from __future__ import annotations
import os, json, sqlite3, datetime
from typing import Any, Dict, List

ASSISTANT_CONFIG_PATH = os.environ.get("ASSISTANT_CONFIG_PATH", r"C:\\bots\\assistant\\config.json")


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _tail_lines(path: str, n: int = 200) -> List[str]:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            size = end
            buf = b""
            lines: List[bytes] = []
            block = 64 * 1024
            while size > 0 and len(lines) <= n:
                step = min(block, size)
                size -= step
                f.seek(size)
                chunk = f.read(step)
                buf = chunk + buf
                lines = buf.split(b"\n")
            if lines and lines[-1] == b"":
                lines = lines[:-1]
            take = lines[-n:] if n < len(lines) else lines
            return [ln.decode("utf-8", errors="ignore") for ln in take]
    except Exception:
        return []



def _repo_root() -> str:
    try:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    except Exception:
        return os.getcwd()


class AssistantLoader:
    def __init__(self) -> None:
        self.cfg = _read_json(ASSISTANT_CONFIG_PATH)
        self.log_dir = (
            os.environ.get("ASSISTANT_LOG_DIR")
            or os.environ.get("ECOSYS_ASSISTANT_LOG_DIR")
            or self.cfg.get("log_dir")
            or r"C:\\bots\\assistant\\logs"
        )
        self.art_dir = (
            os.environ.get("ASSISTANT_ART_DIR")
            or os.environ.get("ECOSYS_ASSISTANT_ART_DIR")
            or self.cfg.get("artifacts")
            or r"C:\\bots\\assistant\\artifacts"
        )
        self.db_path = os.environ.get("ECOSYS_MEMORY_DB", self.cfg.get("memory_db") or r"C:\\bots\\data\\memory.db")
        self.last_session = self.cfg.get("last_session") or ""
        self.assistant_jsonl = os.path.join(self.log_dir, "assistant.jsonl")
        self.tasks_json = os.path.join(self.log_dir, "tasks.json")
        self.repo_state_json = os.path.join(self.log_dir, "repo_state.json")

    def _db_state(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"ok": False}
        if not os.path.exists(self.db_path):
            return out
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            # kv
            kv: Dict[str, Any] = {}
            try:
                for k, v in cur.execute("SELECT key, value FROM kv"):
                    kv[str(k)] = v
            except Exception:
                pass
            # sessions
            session_meta: Dict[str, Any] = {}
            sid = kv.get("last_session") or self.last_session
            if sid:
                try:
                    row = cur.execute(
                        "SELECT id, started_ts, meta_json FROM sessions WHERE id=?", (sid,)
                    ).fetchone()
                    if row:
                        mid = row[0]
                        started_ts = row[1]
                        meta_json = row[2] or "{}"
                        try:
                            meta = json.loads(meta_json)
                        except Exception:
                            meta = {"_raw": meta_json}
                        session_meta = {
                            "id": mid,
                            "started_ts": started_ts,
                            "meta": meta,
                        }
                except Exception:
                    pass
            # notes preview
            notes: List[Dict[str, Any]] = []
            try:
                for row in cur.execute(
                    "SELECT ts, session_id, key, value FROM notes ORDER BY id DESC LIMIT 50"
                ).fetchall():
                    notes.append({
                        "ts": row[0],
                        "session_id": row[1],
                        "key": row[2],
                        "value": row[3],
                    })
                notes.reverse()
            except Exception:
                pass
            con.close()
            out = {"ok": True, "kv": kv, "session": session_meta, "notes": notes}
        except Exception:
            out = {"ok": False}
        return out

    def _tasks(self) -> Dict[str, Any]:
        if not os.path.exists(self.tasks_json):
            return {"ok": False, "tasks": []}
        data = _read_json(self.tasks_json)
        tasks = data.get("tasks") if isinstance(data, dict) else data
        return {"ok": True, "tasks": tasks or []}

    def _repo_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.repo_state_json):
            return {"ok": False}
        return _read_json(self.repo_state_json)

    def resume_snapshot(self) -> Dict[str, Any]:
        dbs = self._db_state()
        logs_tail = _tail_lines(self.assistant_jsonl, 200) if os.path.exists(self.assistant_jsonl) else []
        tasks = self._tasks()
        repo = self._repo_state()
        return {
            "ts": datetime.datetime.now().isoformat(),
            "config": self.cfg,
            "db": dbs,
            "logs_tail": logs_tail,
            "tasks": tasks,
            "repo": repo,
        }

    async def publish_resume(self, bus) -> None:
        snap = self.resume_snapshot()
        # Emit compact resume context
        ctx = {
            "resume": {
                "last_session": snap.get("db", {}).get("session", {}).get("id") or self.last_session,
                "notes": snap.get("db", {}).get("notes", []),
                "tasks_count": len((snap.get("tasks", {}).get("tasks") or [])),
                "logs_tail_count": len(snap.get("logs_tail") or []),
                "repo_state": snap.get("repo", {}),
            }
        }
        await bus.publish("memory/context", ctx, sender="AssistantLoader")
        # Human-friendly line
        human = f"Resuming last session: {ctx['resume'].get('last_session') or 'N/A'} | tasks={ctx['resume']['tasks_count']} | logs_tail={ctx['resume']['logs_tail_count']}"
        await bus.publish("ui/print", {"text": f"AssistantLoader: {human}"}, sender="AssistantLoader")
