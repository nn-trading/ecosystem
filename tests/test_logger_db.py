# Tests for memory.logger_db.LoggerDB
import os
import json
from pathlib import Path

from memory.logger_db import LoggerDB


def test_append_event_and_retrieve(tmp_path):
    db_path = tmp_path / 'logger.db'
    db = LoggerDB(db_path)
    # Append event with searchable text
    payload = {"text": "alpha beta gamma"}
    db.append_event(agent="Tester", type_="note", payload=payload)

    rows = db.retrieve("alpha", k=3)
    assert isinstance(rows, list)
    assert any("alpha" in r.get("snippet", "") for r in rows)


def test_log_tool_event_and_artifact_capture(tmp_path):
    db_path = tmp_path / 'logger.db'
    db = LoggerDB(db_path)

    # Log a tool call and result
    db.log_tool_event('tool/call', {
        'tool': 'x.echo',
        'args': {'text': 'hello'}
    })
    db.log_tool_event('tool/result', {
        'tool': 'x.echo',
        'result': {'text': 'hello world', 'code': 0}
    })

    # Verify events recorded
    cur = db.conn.execute("SELECT COUNT(*) FROM events WHERE agent='ToolRegistry'")
    cnt = cur.fetchone()[0]
    assert cnt >= 2

    # Verify at least one artifact recorded and file exists
    cur = db.conn.execute("SELECT path, meta_json FROM artifacts ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    assert row is not None
    path, meta_json = row
    assert isinstance(path, str) and os.path.exists(path)
    # meta is JSON and should include tool name
    meta = json.loads(meta_json) if meta_json else {}
    assert meta.get('tool') == 'x.echo'
