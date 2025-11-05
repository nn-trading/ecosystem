# tests/test_jobs_queue.py
import sqlite3
from dev.jobs_queue import init, enqueue, pick_one, complete, DB

def test_jobs_flow(tmp_path, monkeypatch):
    # Redirect DB path to temp
    monkeypatch.setattr("dev.jobs_queue.DB", tmp_path/"jobs.db", raising=False)
    init()
    enqueue("status", {})
    j=pick_one(); assert j and j["status"]=="running"
    complete(j["id"], True, None)
    with sqlite3.connect(tmp_path/"jobs.db") as c:
        s=c.execute("SELECT status FROM jobs WHERE id=?", (j["id"],)).fetchone()[0]
        assert s=="done"
