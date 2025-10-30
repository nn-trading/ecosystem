import os, sqlite3, time, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LEGACY_DB = Path('var/events_legacy.db')
LEGACY_DB.parent.mkdir(parents=True, exist_ok=True)

# Create a legacy-style events table with topic/sender
conn = sqlite3.connect(str(LEGACY_DB))
cur = conn.cursor()
cur.executescript('''
DROP TABLE IF EXISTS events;
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  sender TEXT,
  topic TEXT NOT NULL,
  payload_json TEXT
);
''')
conn.commit()

# Seed a couple of rows directly
now = time.time()
cur.execute("INSERT INTO events(ts, sender, topic, payload_json) VALUES (?,?,?,?)", (
    now, 'Main', 'system/heartbeat', json.dumps({'text':'hello legacy heartbeat'}, ensure_ascii=True)
))
cur.execute("INSERT INTO events(ts, sender, topic, payload_json) VALUES (?,?,?,?)", (
    now, 'Main', 'system/health', json.dumps({'text':'legacy health ok'}, ensure_ascii=True)
))
conn.commit()
conn.close()

# Now run LoggerDB on this DB and append one event through the API
os.environ['ECOSYS_LOGGER_DB'] = str(LEGACY_DB)
from memory.logger_db import LoggerDB

db = LoggerDB()
db.append_event(agent='Main', type_='system/heartbeat', payload={'text':'api insert legacy'})
print(json.dumps(db.stats(), ensure_ascii=True))
rows = db.retrieve('legacy', k=5)
print(json.dumps(rows, ensure_ascii=True))
