# dev/metrics_rollup.py
from __future__ import annotations
import sqlite3, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EVENTS=ROOT/"var/events.db"
CHAT=ROOT/"reports/chat/transcript.jsonl"
JDB=ROOT/"var/jobs.db"
OUT=ROOT/"reports/metrics.json"

def count_events():
    try:
        with sqlite3.connect(EVENTS) as c:
            cur=c.execute("SELECT MAX(id), COUNT(*) FROM events")
            mx, cnt = cur.fetchone(); return {"max_id": mx or 0, "total": cnt or 0}
    except Exception: return {"max_id":0,"total":0}

def count_jobs():
    try:
        with sqlite3.connect(JDB) as c:
            tot=c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            pend=c.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
            fail=c.execute("SELECT COUNT(*) FROM jobs WHERE status='failed'").fetchone()[0]
            return {"total":tot,"pending":pend,"failed":fail}
    except Exception: return {"total":0,"pending":0,"failed":0}

def filesize(p:Path): 
    try: return p.stat().st_size
    except Exception: return 0

if __name__=="__main__":
    disk=shutil.disk_usage(str(ROOT))
    out={
        "events": count_events(),
        "jobs": count_jobs(),
        "chat_bytes": filesize(CHAT),
        "disk_free_gb": round(disk.free/1_000_000_000,2),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
    print(str(OUT))
