import os, sys, json, sqlite3, time
from typing import Optional, Tuple

# Ensure repo root on path without relying on external env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory
from memory.eventlog import EventLog

SAFE_TAIL_DEFAULT = int(os.environ.get('IMPORT_SAFE_TAIL', '200'))


def _get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    try:
        cur = conn.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    try:
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, value))
    except Exception:
        pass


def _read_line_bounds(mem: Memory, path: str, meta_key: str, safe_tail: int) -> Tuple[int, int, int]:
    """
    Returns (start_line_inclusive, end_line_inclusive, total_lines)
    start_line_inclusive is last imported line + 1 (meta), or 1 if none.
    end_line_inclusive is total_lines - safe_tail (min 0), to avoid racing with live appends.
    """
    total = mem.count_lines(path)
    end = max(0, total - safe_tail)
    # meta stores the last imported line number; start from next
    start_from = 1
    last = _get_meta(EventLog().conn, meta_key)
    try:
        if last is not None:
            li = int(last)
            if li >= 1:
                start_from = li + 1
    except Exception:
        pass
    return (start_from, end, total)


def _import_events(mem: Memory, elog: EventLog, events_path: str, safe_tail: int) -> dict:
    start, end, total = _read_line_bounds(mem, events_path, 'import.events_line', safe_tail)
    if total == 0 or start > end:
        return {"ok": True, "scanned": 0, "imported": 0, "skipped": total}

    imported = 0
    scanned = 0

    # Snapshot the end bound and iterate once
    conn = elog.conn
    if not conn.in_transaction:
        conn.execute("BEGIN")
    try:
        with open(events_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, ln in enumerate(f, 1):
                if i < start:
                    continue
                if i > end:
                    break
                scanned += 1
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    obj = json.loads(ln)
                except Exception:
                    continue
                ts = float(obj.get('ts') or time.time())
                topic = obj.get('topic') or ''
                sender = obj.get('sender')
                payload = obj.get('payload') or {}
                job_id = obj.get('job_id')
                if job_id is not None and isinstance(payload, dict) and '_job_id' not in payload:
                    payload = {**payload, '_job_id': job_id}
                pj = json.dumps(payload, ensure_ascii=False)
                try:
                    conn.execute(
                        "INSERT INTO events(ts, topic, sender, payload_json) VALUES (?,?,?,?)",
                        (ts, topic, sender, pj)
                    )
                    imported += 1
                except Exception:
                    # Best-effort: ignore duplicates or malformed rows
                    pass
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    # Update resume cursor
    _set_meta(conn, 'import.events_line', str(end))
    return {"ok": True, "scanned": scanned, "imported": imported, "skipped": max(0, (end - start + 1) - imported)}


def _import_summaries(mem: Memory, elog: EventLog, summaries_path: str, safe_tail: int) -> dict:
    start, end, total = _read_line_bounds(mem, summaries_path, 'import.summaries_line', safe_tail)
    if total == 0 or start > end:
        return {"ok": True, "scanned": 0, "imported": 0, "skipped": total}

    imported = 0
    scanned = 0

    conn = elog.conn
    if not conn.in_transaction:
        conn.execute("BEGIN")
    try:
        with open(summaries_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, ln in enumerate(f, 1):
                if i < start:
                    continue
                if i > end:
                    break
                scanned += 1
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    obj = json.loads(ln)
                except Exception:
                    continue
                ts = float(obj.get('ts') or time.time())
                rng = obj.get('range') or [0, 0]
                lines = int(obj.get('lines') or 0)
                text = obj.get('text') or ''
                payload = {"range": rng, "lines": lines, "text": text}
                pj = json.dumps(payload, ensure_ascii=False)
                try:
                    conn.execute(
                        "INSERT INTO events(ts, topic, sender, payload_json) VALUES (?,?,?,?)",
                        (ts, 'memory/summary', 'Memory', pj)
                    )
                    imported += 1
                except Exception:
                    pass
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    _set_meta(conn, 'import.summaries_line', str(end))
    return {"ok": True, "scanned": scanned, "imported": imported, "skipped": max(0, (end - start + 1) - imported)}


def main():
    safe_tail = SAFE_TAIL_DEFAULT
    mem = Memory()
    elog = EventLog()

    events_path = mem.events_path  # type: ignore[attr-defined]
    summaries_path = mem.summaries_path  # type: ignore[attr-defined]

    # Allow overrides via CLI args
    # Usage: python dev/import_jsonl_to_sqlite.py [events_path] [summaries_path] [safe_tail]
    args = sys.argv[1:]
    if len(args) >= 1 and args[0]:
        events_path = args[0]
    if len(args) >= 2 and args[1]:
        summaries_path = args[1]
    if len(args) >= 3 and args[2].isdigit():
        safe_tail = int(args[2])

    # Ensure schema present (EventLog __init__ already does this)

    res_events = {}
    res_summaries = {}

    try:
        if os.path.exists(events_path):
            res_events = _import_events(mem, elog, events_path, safe_tail)
        else:
            res_events = {"ok": True, "error": "events.jsonl not found"}
    except Exception as e:
        res_events = {"ok": False, "error": f"events import failed: {e}"}

    try:
        if os.path.exists(summaries_path):
            res_summaries = _import_summaries(mem, elog, summaries_path, safe_tail)
        else:
            res_summaries = {"ok": True, "error": "summaries.jsonl not found"}
    except Exception as e:
        res_summaries = {"ok": False, "error": f"summaries import failed: {e}"}

    # Log a concise import event into EventLog for audit
    try:
        payload = {
            "tool": "import_jsonl_to_sqlite",
            "safe_tail": safe_tail,
            "events": res_events,
            "summaries": res_summaries,
        }
        elog.append("import/run", "importer", payload)
    except Exception:
        pass

    # Print result for console
    print(json.dumps({"events": res_events, "summaries": res_summaries}, ensure_ascii=True))


if __name__ == '__main__':
    main()
