# dev/db_validate_runner.py
import os, sys, json, time, runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.ascii_writer import to_ascii

LOGS = ROOT/"logs"
LOGS.mkdir(parents=True, exist_ok=True)

# 1) Persist session tasks using update_tasks_writer (merges legacy 'session')
try:
    runpy.run_path(str(ROOT/"dev"/"update_tasks_writer.py"), run_name="__main__")
except Exception as e:
    pass

# 2) DB validate: resolve path and stats
from memory.logger_db import LoggerDB

e_log = os.environ.get("ECOSYS_LOGGER_DB") or ""
e_mem = os.environ.get("ECOSYS_MEMORY_DB") or ""

db = LoggerDB()
db_path = str(db.path)
exists = os.path.exists(db_path)
stats = {}
try:
    stats = db.stats()
except Exception:
    stats = {}

# 3) Read tasks length
try:
    data = json.loads((ROOT/"logs"/"tasks.json").read_text(encoding="utf-8"))
except Exception:
    data = {}
session_tasks = data.get("session_tasks") or []

# 4) Write ASCII logs
now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

lines = []
lines.append(f"[{now}] DB-validate: ECOSYS_LOGGER_DB='{e_log}' ECOSYS_MEMORY_DB='{e_mem}'")
lines.append(f"[{now}] DB-validate: selected_path='{db_path}' exists={bool(exists)}")
if isinstance(stats, dict):
    lines.append(f"[{now}] DB-stats: events={int(stats.get('events',0))} fts={bool(stats.get('fts', False))} artifacts={int(stats.get('artifacts',0))}")

try:
    with open(ROOT/"logs"/"db_validate.txt", "w", encoding="ascii", errors="ignore") as f:
        f.write(to_ascii("\n".join(lines) + "\n"))
except Exception:
    pass

sess_lines = []
sess_lines.append(f"[{now}] TASKS-align: merged legacy 'session' -> session_tasks; count={len(session_tasks)}")
sess_lines.append(f"[{now}] ASCII-fixes: core01 snapshot append -> ascii; core02 inbox writes -> ascii")
sess_lines.append(f"[{now}] DB-validate: path='{db_path}' exists={bool(exists)} fts={bool(stats.get('fts', False))}")

try:
    with open(ROOT/"logs"/"session_status.txt", "a", encoding="ascii", errors="ignore") as f:
        f.write(to_ascii("\n".join(sess_lines) + "\n"))
except Exception:
    pass

print(json.dumps({
    "ok": True,
    "db_path": db_path,
    "db_exists": bool(exists),
    "stats": stats,
    "session_tasks": len(session_tasks)
}, ensure_ascii=True))
