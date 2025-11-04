# C:\bots\ecosys\memory\eventlog.py
from __future__ import annotations

import json, sqlite3, time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import os

# Safe LIKE/FTS helpers
try:
    from dev.search_escape import like_pattern, quote_fts  # type: ignore
except Exception:
    def quote_fts(term: str) -> str:
        s = str(term)
        return '"' + s.replace('"', '""') + '"'
    def like_pattern(term: str, escape_char: str = '\\'):
        s = str(term).replace(escape_char, escape_char + escape_char)
        s = s.replace('%', escape_char + '%').replace('_', escape_char + '_')
        return f"%{s}%", escape_char

# Resolve DB path at runtime so tests or runtime can override via ECOSYS_LOGGER_DB or ECOSYS_MEMORY_DB.
def _default_db_path() -> Path:
    p = os.environ.get("ECOSYS_LOGGER_DB") or os.environ.get("ECOSYS_MEMORY_DB")
    if p:
        try:
            return Path(p)
        except Exception:
            pass
    try:
        root = Path(__file__).resolve().parent.parent
    except Exception:
        root = Path(os.getcwd())
    return root / "var" / "events.db"

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    topic TEXT NOT NULL,
    sender TEXT,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS rollups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_ts REAL NOT NULL,
    summarized_count INTEGER NOT NULL,
    kept_after INTEGER NOT NULL,
    top_topics_json TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- CORE-03: pragmatic indexes and meta version
CREATE INDEX IF NOT EXISTS idx_events_topic_ts ON events(topic, ts);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
PRAGMA user_version=3;
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
USING fts5(payload, content='events', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS events_ai
AFTER INSERT ON events BEGIN
  INSERT INTO events_fts(rowid, payload) VALUES (new.id, new.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_ad
AFTER DELETE ON events BEGIN
  INSERT INTO events_fts(events_fts, rowid, payload) VALUES ('delete', old.id, old.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_au
AFTER UPDATE ON events BEGIN
  INSERT INTO events_fts(events_fts, rowid, payload) VALUES ('delete', old.id, old.payload_json);
  INSERT INTO events_fts(rowid, payload) VALUES (new.id, new.payload_json);
END;
"""

class EventLog:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else _default_db_path()
        try:
            os.makedirs(str(self.db_path.parent), exist_ok=True)
        except Exception:
            pass
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA temp_store=MEMORY;")
        self.fts_ready = False
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA_SQL)
        # Try to enable FTS5; if unavailable, we’ll fall back to LIKE
        try:
            self.conn.executescript(FTS_SQL)
            # quick probe
            self.conn.execute("SELECT * FROM events_fts LIMIT 0")
            self.fts_ready = True
        except Exception:
            self.fts_ready = False
        self.conn.commit()

    def append(self, topic: str, sender: str | None, payload: Dict[str, Any] | None):
        ts = time.time()
        data = payload or {}
        try:
            pj = json.dumps(data, ensure_ascii=True)
        except Exception:
            pj = json.dumps({"_raw": str(data)}, ensure_ascii=True)
        # Mitigate oversized payloads that can blow up SQLite ("string or blob too big")
        try:
            max_bytes = int(os.environ.get("EVENTLOG_MAX_PAYLOAD", "524288"))  # 512 KB default
        except Exception:
            max_bytes = 524288
        try:
            pj_bytes = pj.encode("utf-8", errors="ignore")
        except Exception:
            pj_bytes = pj.encode("utf-8", "ignore")
        if len(pj_bytes) > max_bytes:
            try:
                # Summarize keys and approximate sizes instead of full payload
                approx_sizes = {}
                if isinstance(data, dict):
                    for k, v in list(data.items())[:64]:
                        try:
                            approx_sizes[str(k)] = len(json.dumps(v, ensure_ascii=True).encode("utf-8", "ignore"))
                        except Exception:
                            approx_sizes[str(k)] = len(str(v).encode("utf-8", "ignore"))
                summary = {
                    "_truncated": True,
                    "topic": topic,
                    "approx_bytes": len(pj_bytes),
                    "max_bytes": max_bytes,
                    "keys": list(data.keys())[:64] if isinstance(data, dict) else [],
                    "approx_key_sizes": approx_sizes,
                }
                pj = json.dumps(summary, ensure_ascii=True)
            except Exception:
                pj = json.dumps({"_truncated": True, "topic": topic, "approx_bytes": len(pj_bytes), "max_bytes": max_bytes}, ensure_ascii=True)
        self.conn.execute(
            "INSERT INTO events(ts, topic, sender, payload_json) VALUES (?,?,?,?)",
            (ts, topic, sender, pj),
        )
        self.conn.commit()

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM events")
        return int(cur.fetchone()[0])

    def _min_id_to_keep_for(self, max_keep: int) -> Optional[int]:
        cur = self.conn.execute("SELECT COUNT(*) FROM events")
        total = int(cur.fetchone()[0])
        if total <= max_keep:
            return None
        cur = self.conn.execute(
            "SELECT id FROM events ORDER BY id ASC LIMIT 1 OFFSET ?", (total - max_keep,)
        )
        row = cur.fetchone()
        return int(row[0]) if row else None

    def _top_topics_in_id_range(self, max_id: int) -> List[Tuple[str, int]]:
        cur = self.conn.execute(
            "SELECT topic, COUNT(*) AS c FROM events WHERE id < ? GROUP BY topic ORDER BY c DESC LIMIT 10",
            (max_id,),
        )
        return [(r[0], int(r[1])) for r in cur.fetchall()]

    def rollup(self, max_keep: int = 500_000) -> Dict[str, Any]:
        min_keep_id = self._min_id_to_keep_for(max_keep)
        if min_keep_id is None:
            return {"summarized": 0, "kept": self.count(), "top_topics": []}

        top = self._top_topics_in_id_range(min_keep_id)
        cur = self.conn.execute("SELECT COUNT(*) FROM events WHERE id < ?", (min_keep_id,))
        summarized = int(cur.fetchone()[0])

        self.conn.execute("DELETE FROM events WHERE id < ?", (min_keep_id,))
        self.conn.commit()

        self.conn.execute(
            "INSERT INTO rollups(generated_ts, summarized_count, kept_after, top_topics_json) VALUES (?,?,?,?)",
            (time.time(), summarized, self.count(), json.dumps(top, ensure_ascii=True)),
        )
        self.conn.commit()

        return {"summarized": summarized, "kept": self.count(), "top_topics": top}

    def recent(self, n: int = 200) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT id, ts, topic, sender, payload_json FROM events ORDER BY id DESC LIMIT ?", (n,)
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for (eid, ts, topic, sender, pj) in reversed(rows):  # chronological
            try:
                payload = json.loads(pj) if pj else {}
            except Exception:
                payload = {"_raw": pj}
            out.append({"id": eid, "ts": ts, "topic": topic, "sender": sender, "payload": payload})
        return out

    def stats(self) -> Dict[str, Any]:
        total = self.count()
        cur = self.conn.execute("SELECT MIN(id), MAX(id) FROM events")
        min_id, max_id = cur.fetchone()
        cur = self.conn.execute("SELECT COUNT(*) FROM rollups")
        rollups = int(cur.fetchone()[0])
        return {"total": total, "min_id": min_id, "max_id": max_id, "rollups": rollups, "fts": self.fts_ready}

    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        records: List[tuple] = []

        def _strip_quotes(s: str) -> str:
            s = str(s).strip()
            if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
                return s[1:-1]
            return s

        q_norm = _strip_quotes(query)
        # Precompute LIKE patterns: one for plain text, one for JSON-escaped backslashes
        like1, _ = like_pattern(q_norm)
        like2 = like1
        if "\\" in q_norm:
            like2, _ = like_pattern(q_norm.replace("\\", "\\\\"))

        if self.fts_ready:
            fts_sql = (
                """
                SELECT e.id, e.ts, e.topic, e.sender, e.payload_json
                FROM events e
                JOIN events_fts f ON e.id = f.rowid
                WHERE f.payload MATCH ?
                ORDER BY e.id DESC
                LIMIT ?
                """
            )
            like_sql = (
                """
                SELECT id, ts, topic, sender, payload_json
                FROM events
                WHERE (
                  payload_json LIKE ? ESCAPE '\\' OR
                  payload_json LIKE ? ESCAPE '\\' OR
                  topic LIKE ? ESCAPE '\\'
                )
                ORDER BY id DESC
                LIMIT ?
                """
            )
            topic_like_sql = (
                """
                SELECT id, ts, topic, sender, payload_json
                FROM events
                WHERE topic LIKE ? ESCAPE '\\'
                ORDER BY id DESC
                LIMIT ?
                """
            )
            try:
                cur = self.conn.execute(fts_sql, (query, limit))
                records = cur.fetchall()
            except Exception:
                # Retry by quoting the term for FTS. If that still fails, fall back to LIKE.
                try:
                    q = '"' + str(query).replace('"', '""') + '"'
                    cur = self.conn.execute(fts_sql, (q, limit))
                    records = cur.fetchall()
                except Exception:
                    cur = self.conn.execute(like_sql, (like1, like2, like1, limit))
                    records = cur.fetchall()
            # If FTS succeeded but returned nothing and the query looks like a topic or contains specials,
            # try targeted LIKEs
            if not records:
                if q_norm.startswith("topic:"):
                    val = q_norm[len("topic:") :]
                    like_t, _ = like_pattern(val)
                    cur = self.conn.execute(topic_like_sql, (like_t, limit))
                    records = cur.fetchall()
                elif q_norm.startswith("topic="):
                    val = q_norm[len("topic=") :]
                    like_t, _ = like_pattern(val)
                    cur = self.conn.execute(topic_like_sql, (like_t, limit))
                    records = cur.fetchall()
            if not records and ("/" in q_norm or ":" in q_norm or " " in q_norm or q_norm != query):
                cur = self.conn.execute(like_sql, (like1, like2, like1, limit))
                records = cur.fetchall()
        else:
            like_sql = (
                """
                SELECT id, ts, topic, sender, payload_json
                FROM events
                WHERE (
                  payload_json LIKE ? ESCAPE '\\' OR
                  payload_json LIKE ? ESCAPE '\\' OR
                  topic LIKE ? ESCAPE '\\'
                )
                ORDER BY id DESC
                LIMIT ?
                """
            )
            cur = self.conn.execute(like_sql, (like1, like2, like1, limit))
            records = cur.fetchall()

        for (eid, ts, topic, sender, pj) in records:
            try:
                payload = json.loads(pj) if pj else {}
            except Exception:
                payload = {"_raw": pj}
            out.append({"id": eid, "ts": ts, "topic": topic, "sender": sender, "payload": payload})
        # return chronological
        return list(reversed(out))
