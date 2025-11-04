# Tests for EventLog.search FTS and LIKE fallback paths (ASCII-only)
import os, sqlite3, tempfile, uuid, json
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


def test_like_topic_percent_underscore_backslash_literals():
    db_path = with_temp_db()
    ev = EventLog(db_path)
    t1 = "a%b"
    t2 = "a_b"
    t3 = r"C:\\tmp\\alpha"
    ev.append(t1, "tester", {"text": "percent case"})
    ev.append(t2, "tester", {"text": "underscore case"})
    ev.append(t3, "tester", {"text": "backslash case"})

    rows1 = ev.search("topic=" + t1, limit=10)
    assert any(r.get("topic") == t1 for r in rows1), "Percent should be treated literally in topic LIKE"

    rows2 = ev.search("topic=" + t2, limit=10)
    assert any(r.get("topic") == t2 for r in rows2), "Underscore should be treated literally in topic LIKE"

    rows3 = ev.search("topic=" + t3, limit=10)
    assert any(r.get("topic") == t3 for r in rows3), "Backslash should be matched literally in topic LIKE"


def test_like_payload_specials_when_non_fts_path():
    db_path = with_temp_db()
    ev = EventLog(db_path)
    ev.fts_ready = False
    ev.append("ui/print", "tester", {"text": "value is 100% ready"})
    ev.append("ui/print", "tester", {"path": r"C:\\tmp\\alpha"})

    rows_pct = ev.search("100% ready", limit=10)
    assert rows_pct and any("100% ready" in (r.get("payload", {}).get("text", "") if isinstance(r.get("payload"), dict) else str(r.get("payload"))) for r in rows_pct)

    rows_bs = ev.search(r"C:\\tmp\\alpha", limit=10)
    expected = r"C:\\tmp\\alpha"
    assert rows_bs and any(isinstance(r.get("payload"), dict) and r["payload"].get("path") in (expected, expected.replace('\\','/')) for r in rows_bs)



