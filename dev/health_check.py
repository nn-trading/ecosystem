import os, sys, time, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memory.eventlog import EventLog

CHECKS = [
    ('chat bridge cursor', "SELECT value FROM meta WHERE key='bridge.chat_last_id'"),
    ('events total', "SELECT COUNT(*) FROM events"),
    ('rollups total', "SELECT COUNT(*) FROM rollups"),
]

OK = True

try:
    el = EventLog()
    cur = el.conn.cursor()
    results = []
    for name, sql in CHECKS:
        try:
            row = cur.execute(sql).fetchone()
            val = row[0] if row else None
            results.append((name, val))
        except Exception as e:
            OK = False
            results.append((name, f'ERR: {e}'))

    payload = {
        'ts': time.time(),
        'ok': OK,
        'results': results,
    }
    el.append('system/health', 'health_check', payload)
    print(json.dumps(payload, ensure_ascii=True))
except Exception as e:
    print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=True))
