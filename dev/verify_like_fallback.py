import os, json, sqlite3, sys
from pathlib import Path

# Ensure repo root on sys.path for `memory` package import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory.logger_db import LoggerDB

db_arg = sys.argv[1] if len(sys.argv) > 1 else 'var/events_legacy.db'
q = sys.argv[2] if len(sys.argv) > 2 else 'legacy'
p = Path(db_arg).resolve()
os.environ['ECOSYS_LOGGER_DB'] = str(p)

db = LoggerDB(db_path=p)
print('DB:', str(p))
print('stats_before:', json.dumps(db.stats()))

try:
    db.conn.execute('DROP TABLE IF EXISTS events_fts')
    db.conn.commit()
    print('events_fts dropped')
except Exception as e:
    print('drop_error:', repr(e))

print('stats_after_drop:', json.dumps(db.stats()))

s = db.stats()
if int(s.get('events', 0)) == 0:
    try:
        db.conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, sender TEXT, topic TEXT, payload_json TEXT)")
        db.conn.execute("INSERT INTO events(ts, sender, topic, payload_json) VALUES (strftime('%s','now'), 'legacy-seed', 'legacy', '{\"text\":\"seed legacy content\"}')")
        db.conn.commit()
        print('seeded one legacy row')
    except Exception as e:
        print('seed_error:', repr(e))

res = db.retrieve(q, k=5)
print('retrieve_fallback_count:', len(res))
for r in res:
    print('res_item:', json.dumps(r, ensure_ascii=True))
