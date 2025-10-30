# C:\bots\ecosys\memory\logger_db.py
from __future__ import annotations
import os, json, sqlite3, time, threading, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DB_PATH = Path(
	    os.environ.get("ECOSYS_LOGGER_DB")
	    or os.environ.get("ECOSYS_MEMORY_DB")
	    or (Path(__file__).resolve().parent.parent / "var" / "events.db")
	)
_DB_LOCK = threading.RLock()
_RUN_TS: Optional[str] = None

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  agent TEXT,
  type TEXT NOT NULL,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  title TEXT,
  body TEXT
);

CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  text TEXT
);

-- FTS for retrieval (optional)
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(payload, type, agent, content='events', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
  INSERT INTO events_fts(rowid, payload, type, agent) VALUES (new.id, new.payload_json, new.type, new.agent);
END;
CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
  INSERT INTO events_fts(events_fts, rowid, payload, type, agent) VALUES ('delete', old.id, old.payload_json, old.type, old.agent);
  INSERT INTO events_fts(rowid, payload, type, agent) VALUES (new.id, new.payload_json, new.type, new.agent);
END;
CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
  INSERT INTO events_fts(events_fts, rowid, payload, type, agent) VALUES ('delete', old.id, old.payload_json, old.type, old.agent);
END;
"""

class LoggerDB:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.path = Path(db_path) if db_path else _DB_PATH
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def _json(self, data: Any) -> str:
        try:
            return json.dumps(data, ensure_ascii=True)
        except Exception:
            try:
                return json.dumps({"_raw": str(data)}, ensure_ascii=True)
            except Exception:
                return "{}"

    def append_event(self, agent: Optional[str], type_: str, payload: Optional[Dict[str, Any]] = None) -> None:
        with _DB_LOCK:
            self.conn.execute(
                "INSERT INTO events(ts, agent, type, payload_json) VALUES (?,?,?,?)",
                (time.time(), agent, type_, self._json(payload or {})),
            )
            self.conn.commit()

    def log_tool_event(self, topic: str, data: Dict[str, Any]) -> None:
        # topic in {"tool/call","tool/result"}. Data contains tool name, args or result
        try:
            tool = str(data.get("tool", ""))
            payload = {**data}
            payload["_topic"] = topic
            payload["_tool"] = tool
            self.append_event(agent="ToolRegistry", type_=topic, payload=payload)
            if topic == "tool/result":
                self._maybe_capture_artifact(tool, payload)
        except Exception:
            pass

    def _ensure_run_dir(self) -> Path:
        global _RUN_TS
        runs = Path(__file__).resolve().parent.parent / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        if not _RUN_TS:
            _RUN_TS = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        rd = runs / _RUN_TS
        rd.mkdir(parents=True, exist_ok=True)
        return rd

    def _sha256_file(self, path: Path) -> Optional[str]:
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _write_text_artifact(self, name: str, text: str) -> Optional[Path]:
        try:
            rd = self._ensure_run_dir()
            safe = name.replace("/", "_").replace("\\", "_")[:60]
            p = rd / f"artifact_{int(time.time())}_{safe}.txt"
            with open(p, "w", encoding="ascii", errors="ignore") as f:
                f.write(text)
                if not text.endswith("\n"):
                    f.write("\n")
            return p
        except Exception:
            return None

    def _maybe_capture_artifact(self, tool: str, payload: Dict[str, Any]) -> None:
        # Try to persist common textual outputs
        res = payload.get("result") if isinstance(payload, dict) else None
        if isinstance(res, dict):
            # File path output
            path = res.get("path")
            if isinstance(path, str) and os.path.exists(path):
                sha = self._sha256_file(Path(path))
                meta = {"tool": tool}
                self.add_artifact(Path(path), sha256=sha, meta=meta)
            # stdout/text outputs
            txt = None
            for k in ("stdout", "text", "content"):
                v = res.get(k)
                if isinstance(v, str) and v.strip():
                    txt = v
                    break
            if txt:
                ap = self._write_text_artifact(f"{tool}", txt)
                if ap:
                    self.add_artifact(ap, sha256=self._sha256_file(ap), meta={"tool": tool, "derived": True})

    def add_artifact(self, path: Path, sha256: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> None:
        meta_json = self._json(meta or {})
        with _DB_LOCK:
            self.conn.execute(
                "INSERT INTO artifacts(ts, path, sha256, meta_json) VALUES (?,?,?,?)",
                (time.time(), str(path), sha256, meta_json),
            )
            self.conn.commit()

    def add_skill(self, title: str, body: str = "") -> None:
        with _DB_LOCK:
            self.conn.execute(
                "INSERT INTO skills(ts, title, body) VALUES (?,?,?)",
                (time.time(), title, body),
            )
            self.conn.commit()

    def add_memory(self, text: str) -> None:
        # Store as-is (may contain Unicode). SQLite can handle it; file artifacts remain ASCII-safe
        with _DB_LOCK:
            self.conn.execute(
                "INSERT INTO memories(ts, text) VALUES (?,?)",
                (time.time(), str(text or "")),
            )
            self.conn.commit()

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not query:
            return []
        try:
            sql = (
                "SELECT e.ts, e.agent, e.type, e.payload_json FROM events e "
                "JOIN events_fts f ON e.id=f.rowid WHERE f.payload MATCH ? ORDER BY e.id DESC LIMIT ?"
            )
            args = (query, int(k))
            cur = self.conn.execute(sql, args)
        except Exception:
            like = f"%{query}%"
            cur = self.conn.execute(
                "SELECT ts, agent, type, payload_json FROM events WHERE (payload_json LIKE ? OR type LIKE ? OR agent LIKE ?) ORDER BY id DESC LIMIT ?",
                (like, like, like, int(k)),
            )
        out: List[Dict[str, Any]] = []
        rows = cur.fetchall()
        for (ts, agent, type_, pj) in rows:
            snippet = ""
            try:
                d = json.loads(pj) if pj else {}
                if isinstance(d, dict):
                    # prefer short summary
                    for key in ("text","stdout","error","message"):
                        if key in d and isinstance(d[key], str):
                            snippet = d[key][:400]
                            break
                    if not snippet:
                        snippet = json.dumps(d, ensure_ascii=True)[:400]
                else:
                    snippet = str(d)[:400]
            except Exception:
                snippet = (pj or "")[:400]
            out.append({"ts": ts, "agent": agent, "type": type_, "snippet": snippet})
        out.reverse()  # return chronological
        return out

_singleton: Optional[LoggerDB] = None

def get_logger_db() -> LoggerDB:
    global _singleton
    if _singleton is None:
        _singleton = LoggerDB()
    return _singleton
