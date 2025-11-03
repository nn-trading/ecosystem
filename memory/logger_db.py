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

CREATE TABLE IF NOT EXISTS tools (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  name TEXT NOT NULL,
  version TEXT,
  provider TEXT,
  meta_json TEXT
);

-- FTS for retrieval (optional)
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(payload, type, agent, content='events', content_rowid='id');


"""

class LoggerDB:
    def __init__(self, db_path: Optional[Path] = None, allow_mirror: bool = True) -> None:
        self.path = Path(db_path) if db_path else _DB_PATH
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._ensure_schema_compat()
        self._ensure_fts_triggers_compat()
        # Optional mirror DB for dual-write observability (no wipe)
        self._mirror: Optional[LoggerDB] = None  # type: ignore[name-defined]
        try:
            if db_path is None and allow_mirror and not os.environ.get("ECOSYS_DISABLE_MIRROR"):
                repo = Path(__file__).resolve().parent.parent
                mirror_path = repo / "data" / "ecosys.db"
                if mirror_path != self.path:
                    # Ensure parent exists and initialize without further mirroring
                    mirror_path.parent.mkdir(parents=True, exist_ok=True)
                    self._mirror = LoggerDB(mirror_path, allow_mirror=False)
        except Exception:
            # Never fail construction due to mirror problems
            self._mirror = None

    def _ensure_schema_compat(self) -> None:
        cols = self._columns("events")
        if "agent" not in cols:
            try:
                with _DB_LOCK:
                    self.conn.execute("ALTER TABLE events ADD COLUMN agent TEXT")
                    self.conn.commit()
            except Exception:
                pass
        # Do not try to add 'type' automatically; older DBs may use 'topic'


    def _ensure_fts_triggers_compat(self) -> None:
        type_col, agent_col = self._event_colnames()
        t_new = f"new.{type_col}" if type_col else "NULL"
        a_new = f"new.{agent_col}" if agent_col else "NULL"
        t_old = f"old.{type_col}" if type_col else "NULL"
        a_old = f"old.{agent_col}" if agent_col else "NULL"
        sql = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(payload, type, agent, content='events', content_rowid='id');
DROP TRIGGER IF EXISTS events_ai;
CREATE TRIGGER events_ai AFTER INSERT ON events BEGIN
  INSERT INTO events_fts(rowid, payload, type, agent) VALUES (new.id, new.payload_json, {t_new}, {a_new});
END;
DROP TRIGGER IF EXISTS events_au;
CREATE TRIGGER events_au AFTER UPDATE ON events BEGIN
  INSERT INTO events_fts(events_fts, rowid, payload, type, agent) VALUES ('delete', old.id, old.payload_json, {t_old}, {a_old});
  INSERT INTO events_fts(rowid, payload, type, agent) VALUES (new.id, new.payload_json, {t_new}, {a_new});
END;
DROP TRIGGER IF EXISTS events_ad;
CREATE TRIGGER events_ad AFTER DELETE ON events BEGIN
  INSERT INTO events_fts(events_fts, rowid, payload, type, agent) VALUES ('delete', old.id, old.payload_json, {t_old}, {a_old});
END;
"""
        with _DB_LOCK:
            try:
                self.conn.executescript(sql)
                # Backfill FTS if empty (handles legacy DBs with existing rows)
                try:
                    cur = self.conn.execute("SELECT 1 FROM events_fts LIMIT 1")
                    has = cur.fetchone()
                except Exception:
                    has = True  # if querying FTS fails, skip backfill
                if not has:
                    t_sel = type_col if type_col else "NULL"
                    a_sel = agent_col if agent_col else "NULL"
                    self.conn.execute(
                        f"INSERT INTO events_fts(rowid, payload, type, agent) SELECT id, payload_json, {t_sel}, {a_sel} FROM events"
                    )
                self.conn.commit()
            except Exception:
                pass


    def _columns(self, table: str) -> List[str]:
        try:
            cur = self.conn.execute(f"PRAGMA table_info({table})")
            return [str(r[1]) for r in cur.fetchall()]
        except Exception:
            return []

    def _event_colnames(self) -> Tuple[Optional[str], Optional[str]]:
        cols = set(self._columns("events"))
        type_col = 'type' if 'type' in cols else ('topic' if 'topic' in cols else None)
        agent_col = 'agent' if 'agent' in cols else ('sender' if 'sender' in cols else None)
        return type_col, agent_col

    def _json(self, data: Any) -> str:
        try:
            return json.dumps(data, ensure_ascii=True)
        except Exception:
            try:
                return json.dumps({"_raw": str(data)}, ensure_ascii=True)
            except Exception:
                return "{}"

    def append_event(self, agent: Optional[str], type_: str, payload: Optional[Dict[str, Any]] = None) -> None:
        cols = set(self._columns("events"))
        names: List[str] = ["ts"]
        vals: List[Any] = [time.time()]
        if "agent" in cols:
            names.append("agent"); vals.append(agent)
        elif "sender" in cols:
            names.append("sender"); vals.append(agent)
        if "type" in cols:
            names.append("type"); vals.append(type_)
        elif "topic" in cols:
            names.append("topic"); vals.append(type_)
        names.append("payload_json"); vals.append(self._json(payload or {}))
        q = ",".join(["?" for _ in names])
        sql = f"INSERT INTO events({', '.join(names)}) VALUES ({q})"
        with _DB_LOCK:
            self.conn.execute(sql, tuple(vals))
            self.conn.commit()
        # Mirror write
        try:
            if getattr(self, "_mirror", None):
                # Use mirror's append_event to preserve its own schema/triggers
                self._mirror.append_event(agent, type_, payload)
        except Exception:
            pass

    def log_tool_event(self, topic: str, data: Dict[str, Any]) -> None:
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
        res = payload.get("result") if isinstance(payload, dict) else None
        if isinstance(res, dict):
            path = res.get("path")
            if isinstance(path, str) and os.path.exists(path):
                sha = self._sha256_file(Path(path))
                meta = {"tool": tool}
                self.add_artifact(Path(path), sha256=sha, meta=meta)
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
        try:
            if getattr(self, "_mirror", None):
                self._mirror.add_artifact(path, sha256=sha256, meta=meta)
        except Exception:
            pass

    def add_skill(self, title: str, body: str = "") -> None:
        with _DB_LOCK:
            self.conn.execute(
                "INSERT INTO skills(ts, title, body) VALUES (?,?,?)",
                (time.time(), title, body),
            )
            self.conn.commit()
        try:
            if getattr(self, "_mirror", None):
                self._mirror.add_skill(title, body)
        except Exception:
            pass

    def add_memory(self, text: str) -> None:
        with _DB_LOCK:
            self.conn.execute(
                "INSERT INTO memories(ts, text) VALUES (?,?)",
                (time.time(), str(text or "")),
            )
            self.conn.commit()
        try:
            if getattr(self, "_mirror", None):
                self._mirror.add_memory(text)
        except Exception:
            pass

    def stats(self) -> Dict[str, Any]:
        with _DB_LOCK:
            try:
                total, min_id, max_id = self.conn.execute(
                    "SELECT COUNT(*), MIN(id), MAX(id) FROM events"
                ).fetchone()
            except Exception:
                total, min_id, max_id = 0, None, None
            def _count(tbl: str) -> int:
                try:
                    return int(self.conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0])
                except Exception:
                    return 0
            artifacts = _count("artifacts")
            skills = _count("skills")
            memories = _count("memories")
            tools = _count("tools")
            fts = True
            try:
                self.conn.execute("SELECT rowid FROM events_fts LIMIT 0")
            except Exception:
                fts = False
            return {
                "events": int(total or 0),
                "min_id": min_id,
                "max_id": max_id,
                "artifacts": artifacts,
                "skills": skills,
                "memories": memories,
                "tools": tools,
                "fts": fts,
            }

    def add_tool(self, name: str, version: Optional[str] = None, provider: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> None:
        meta_json = self._json(meta or {})
        with _DB_LOCK:
            self.conn.execute(
                "INSERT INTO tools(ts, name, version, provider, meta_json) VALUES (?,?,?,?,?)",
                (time.time(), name, version, provider, meta_json),
            )
            self.conn.commit()
        try:
            if getattr(self, "_mirror", None):
                self._mirror.add_tool(name, version=version, provider=provider, meta=meta)
        except Exception:
            pass

    def recent_events(self, n: int = 200) -> List[Dict[str, Any]]:
        type_col, agent_col = self._event_colnames()
        sel_parts = ["id", "ts"]
        if agent_col:
            sel_parts.append(agent_col + " AS agent")
        else:
            sel_parts.append("NULL AS agent")
        if type_col:
            sel_parts.append(type_col + " AS type")
        else:
            sel_parts.append("NULL AS type")
        sel_parts.append("payload_json")
        sql = f"SELECT {', '.join(sel_parts)} FROM events ORDER BY id DESC LIMIT ?"
        cur = self.conn.execute(sql, (int(n),))
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for (eid, ts, agent, type_, pj) in reversed(rows):
            try:
                payload = json.loads(pj) if pj else {}
            except Exception:
                payload = {"_raw": pj}
            out.append({"id": eid, "ts": ts, "agent": agent, "type": type_, "payload": payload})
        return out

    def recent_artifacts(self, n: int = 200) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT id, ts, path, sha256, meta_json FROM artifacts ORDER BY id DESC LIMIT ?",
            (int(n),),
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for (aid, ts, path, sha, mj) in reversed(rows):
            try:
                meta = json.loads(mj) if mj else {}
            except Exception:
                meta = {"_raw": mj}
            out.append({"id": aid, "ts": ts, "path": path, "sha256": sha, "meta": meta})
        return out

    def top_event_types(self, limit: int = 10) -> List[Tuple[str, int]]:
        type_col, _ = self._event_colnames()
        if not type_col:
            return []
        cur = self.conn.execute(
            f"SELECT {type_col} AS type, COUNT(*) AS c FROM events WHERE {type_col} IS NOT NULL GROUP BY {type_col} ORDER BY c DESC LIMIT ?",
            (int(limit),),
        )
        return [(r[0], int(r[1])) for r in cur.fetchall()]

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not query:
            return []
        type_col, agent_col = self._event_colnames()
        rows: List[tuple] = []
        try:
            sel_parts = ["e.id", "e.ts"]
            sel_parts.append(f"e.{agent_col} AS agent" if agent_col else "NULL AS agent")
            sel_parts.append(f"e.{type_col} AS type" if type_col else "NULL AS type")
            sel_parts.append("e.payload_json")
            sql = (
                f"SELECT {', '.join(sel_parts)} FROM events e "
                "JOIN events_fts f ON e.id=f.rowid WHERE f.payload MATCH ? ORDER BY e.id DESC LIMIT ?"
            )
            cur = self.conn.execute(sql, (query, int(k)))
            rows = cur.fetchall()
            if not rows and any(ch in str(query) for ch in ('/', ':', ' ', '*', '"', "'", '\\', '|')):
                raise RuntimeError('fts_empty_fallback')
        except Exception:
            like = f"%{query}%"
            where_bits = ["payload_json LIKE ?"]
            params: List[Any] = [like]
            if type_col:
                where_bits.append(f"{type_col} LIKE ?")
                params.append(like)
            if agent_col:
                where_bits.append(f"{agent_col} LIKE ?")
                params.append(like)
            sel_parts = ["id", "ts"]
            sel_parts.append(f"{agent_col} AS agent" if agent_col else "NULL AS agent")
            sel_parts.append(f"{type_col} AS type" if type_col else "NULL AS type")
            sel_parts.append("payload_json")
            sql = f"SELECT {', '.join(sel_parts)} FROM events WHERE (" + " OR ".join(where_bits) + ") ORDER BY id DESC LIMIT ?"
            params.append(int(k))
            cur = self.conn.execute(sql, tuple(params))
            rows = cur.fetchall()
        dedup: Dict[int, Dict[str, Any]] = {}
        for (eid, ts, agent, type_, pj) in rows:
            snippet = ""
            try:
                d = json.loads(pj) if pj else {}
                if isinstance(d, dict):
                    for key in ("text", "stdout", "error", "message"):
                        if key in d and isinstance(d[key], str):
                            snippet = d[key][:400]
                            break
                    if not snippet:
                        snippet = json.dumps(d, ensure_ascii=True)[:400]
                else:
                    snippet = str(d)[:400]
            except Exception:
                snippet = (pj or "")[:400]
            dedup[int(eid)] = {"id": int(eid), "ts": ts, "agent": agent, "type": type_, "snippet": snippet}
        # Return in ascending id order
        out = [dedup[k] for k in sorted(dedup.keys())]
        return out

_singleton: Optional[LoggerDB] = None

def get_logger_db() -> LoggerDB:
    global _singleton
    if _singleton is None:
        _singleton = LoggerDB()
    return _singleton
