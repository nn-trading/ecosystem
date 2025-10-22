import os, json, time
import sqlite3

# Ensure repo root on path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory.eventlog import EventLog
from core.memory import Memory


def main():
    el = EventLog()
    cur = el.conn.cursor()
    meta_pairs = cur.execute("select key, value from meta").fetchall()
    meta = {k: v for (k, v) in meta_pairs}

    mem = Memory()
    stats = mem.stats()

    payload = {
        "meta": meta,
        "memory": stats,
        "ts": time.time(),
    }

    # Log an event for audit and quick resume reference
    el.append("resume/cursor", "runner", payload)

    # Also persist a compact summary string in meta for quick access
    try:
        summary = json.dumps({"meta": meta, "events_lines": stats.get("events_lines", 0)}, ensure_ascii=True)
        el.conn.execute("insert or replace into meta(key, value) values (?, ?)", ("import.resume_summary", summary))
        el.conn.commit()
    except Exception:
        pass

    print("resume_meta_logged")


if __name__ == "__main__":
    main()
