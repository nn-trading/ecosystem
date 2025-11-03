# Tests for EventLog.search FTS and LIKE fallback paths (ASCII-only)
import os, sqlite3, tempfile, uuid
from memory.eventlog import EventLog


def with_temp_db():
    db = os.path.join(tempfile.gettempdir(), f"ecosys_test_{uuid.uuid4().hex}.db")
    os.environ['ECOSYS_MEMORY_DB'] = db
    return db


def test_eventlog_search_like_fallback_when_fts_empty():
    db_path = with_temp_db()
    ev = EventLog(db_path)
    ev.append("ui/print", "tester", {"text": "open http://alpha/beta now"})
    # Force FTS index empty, so initial FTS search yields 0 rows
    try:
        ev.conn.execute("DELETE FROM events_fts")
        ev.conn.commit()
    except Exception:
        pass
    rows = ev.search("ui/print", limit=5)
    assert rows, "LIKE fallback should find by topic when FTS returns empty"
    assert any(r.get("topic") == "ui/print" for r in rows)


def test_eventlog_search_basic_fts_success():
    db_path = with_temp_db()
    ev = EventLog(db_path)
    ev.append("ui/print", "tester", {"text": "alpha beta gamma"})
    rows = ev.search("alpha", limit=5)
    assert rows, "FTS path should return rows for simple token"
    assert any("alpha" in (r.get("payload", {}).get("text", "") if isinstance(r.get("payload"), dict) else str(r.get("payload"))) for r in rows)
