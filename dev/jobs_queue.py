# dev/jobs_queue.py
from __future__ import annotations
import sqlite3, json, time, subprocess, argparse, os, sys, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"var/jobs.db"
LOG_DIR=ROOT/"logs/jobs"

def to_ascii(s:str)->str:
    try:
        return (s or "").encode("ascii","ignore").decode("ascii")
    except Exception:
        return ""

PY=str((ROOT/".venv/Scripts/python.exe").resolve())
if not os.path.exists(PY):
    py_cmd = shutil.which("python") or shutil.which("py")
    PY = py_cmd if py_cmd else "python"

def init():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS jobs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts DATETIME DEFAULT CURRENT_TIMESTAMP,
          kind TEXT, payload TEXT,
          status TEXT DEFAULT 'pending',
          tries INTEGER DEFAULT 0,
          last_error TEXT)""")
        c.commit()

def enqueue(kind:str, payload:dict):
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO jobs(kind,payload) VALUES(?,?)",(kind,json.dumps(payload,ensure_ascii=True)))
        c.commit()

def pick_one():
    with sqlite3.connect(DB) as c:
        c.row_factory=sqlite3.Row
        r=c.execute("SELECT * FROM jobs WHERE status='pending' ORDER BY id ASC LIMIT 1").fetchone()
        if not r: return None
        c.execute("UPDATE jobs SET status='running', tries=tries+1 WHERE id=?",(r["id"],));
        c.commit()
        d = dict(r)
        d["status"] = "running"
        try:
            d["tries"] = int(d.get("tries", 0)) + 1
        except Exception:
            d["tries"] = (d.get("tries") or 0) + 1
        return d

def complete(id:int, ok:bool, err:str|None):
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE jobs SET status=?, last_error=? WHERE id=?",
                  ("done" if ok else "failed", to_ascii((err or "")[:500]), id))
        c.commit()


def retry(id:int, err:str|None):
    e = to_ascii((err or "")[:500])
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE jobs SET status='pending', last_error=? WHERE id=?", (e, id))
        c.commit()

def do_job(j):
    kind=j["kind"]; payload=json.loads(j.get("payload") or "{}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"job_{j['id']}.log"
    def run(args):
        return subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT))
    try:
        if kind=="plan_apply":
            msg=payload.get("ask") or "Create a tiny echo agent and a tiny tool"
            run([PY,"dev/chatops_cli.py", msg])
            r=run([PY,"dev/core02_planner.py","apply"])
            ok=(r.returncode==0)
            log_path.write_text(to_ascii((r.stdout or "") + "\n" + (r.stderr or ""))[:5000], encoding="utf-8")
            return ok, to_ascii(r.stdout)[-1000:]
        if kind=="rollup_chat":
            r=run([PY,"dev/chat_summarizer.py"])
            log_path.write_text(to_ascii((r.stdout or "") + "\n" + (r.stderr or ""))[:5000], encoding="utf-8")
            return (r.returncode==0), to_ascii(r.stdout)[-1000:]
        if kind=="snapshot":
            r=run([PY,"dev/loggerdb_cli.py","snapshot-run","-n","200"])
            log_path.write_text(to_ascii((r.stdout or "") + "\n" + (r.stderr or ""))[:5000], encoding="utf-8")
            return (r.returncode==0), to_ascii(r.stdout)[-1000:]
        if kind=="db_vacuum":
            r=run([PY,"dev/db_cli.py","vacuum"])
            log_path.write_text(to_ascii((r.stdout or "") + "\n" + (r.stderr or ""))[:5000], encoding="utf-8")
            return (r.returncode==0), to_ascii(r.stdout)[-1000:]
        if kind=="status":
            r=run([PY,"dev/obs_cli.py","stats"])
            log_path.write_text(to_ascii((r.stdout or "") + "\n" + (r.stderr or ""))[:5000], encoding="utf-8")
            return (r.returncode==0), to_ascii(r.stdout)[-1000:]
        log_path.write_text(f"unknown kind: {kind}", encoding="utf-8")
        return False, f"unknown kind: {kind}"
    except Exception as e:
        log_path.write_text(to_ascii(str(e)), encoding="utf-8")
        return False, str(e)

def loop(interval:int=5, max_tries:int=3):
    init()
    while True:
        j=pick_one()
        if not j:
            time.sleep(interval); continue
        ok=False; err=None; msg=None
        try:
            ok, msg = do_job(j)
        except Exception as e:
            ok=False; err=str(e)
        err_msg = to_ascii(((err or msg) or "")[:500])
        if ok:
            complete(j["id"], True, "")
        else:
            if j.get("tries",0) >= max_tries:
                complete(j["id"], False, err_msg or "max_tries")
            else:
                retry(j["id"], err_msg or "retry")
                # simple backoff based on tries
                try:
                    delay = min(60, 2 ** max(0, int(j.get("tries",1))-1))
                except Exception:
                    delay = 1
                time.sleep(delay)
        time.sleep(0.5)

def list_jobs():
    with sqlite3.connect(DB) as c:
        for row in c.execute("SELECT id,ts,kind,status,tries FROM jobs ORDER BY id DESC LIMIT 50"):
            print(row)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["enqueue","run","list"])
    ap.add_argument("--kind"); ap.add_argument("--payload")
    ap.add_argument("--loop", action="store_true"); ap.add_argument("--interval", type=int, default=5)
    args=ap.parse_args()
    init()
    if args.cmd=="enqueue":
        kind=args.kind or "status"
        payload=json.loads(args.payload or "{}"); enqueue(kind,payload); print("enqueued")
    elif args.cmd=="list":
        list_jobs()
    elif args.cmd=="run":
        if args.loop: loop(interval=args.interval)
        else:
            j=pick_one()
            print("none" if not j else json.dumps(j))
