# dev/sqlite_inspect.py
import os, sys, json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memory.eventlog import EventLog

def main():
    el = EventLog()
    stats = el.stats()
    recent = el.recent(20)
    out = {
        'stats': stats,
        'recent_topics': [ (r['id'], r['topic'], r.get('sender')) for r in recent ],
    }
    print(json.dumps(out, ensure_ascii=True))

if __name__ == '__main__':
    main()
