import os, json, sys
# Ensure repo root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memory.eventlog import EventLog

def main():
    el = EventLog()
    stats = el.stats()
    cur = el.conn.cursor()
    meta_import = {k: v for (k, v) in cur.execute("select key, value from meta where key like 'import.%'")}
    recent = el.recent(3)
    out = {
        "events": stats.get("total"),
        "rollups": stats.get("rollups"),
        "fts": stats.get("fts"),
        "meta_import_keys": sorted(list(meta_import.keys())),
        "recent_topics": [(r["topic"], r.get("sender")) for r in recent],
    }
    print(json.dumps(out, ensure_ascii=True))

if __name__ == "__main__":
    main()
