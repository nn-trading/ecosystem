# Enqueue and process a single plan_apply job; update ASCII logs and tasks report
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from dev import jobs_queue as jq  # type: ignore

logs = ROOT / 'logs'
logs.mkdir(exist_ok=True)

jq.init()
jq.enqueue('plan_apply', {'ask': 'Add tiny TODO demo tool and run apply'})

j = jq.pick_one()
ok = False
msg = ''
if j:
    ok, msg = jq.do_job(j)
    jq.complete(j['id'], ok, '' if ok else (msg[-200:] if isinstance(msg, str) else 'error'))

# Update logs/tasks.json: set MAXCAP-STEP-6 to done if ok
tasks_file = logs / 'tasks.json'
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
data = {'ts': now, 'tasks': []}
if tasks_file.exists():
    try:
        data = json.loads(tasks_file.read_text('utf-8') or '{}') or {'tasks': []}
    except Exception:
        data = {'tasks': []}

found = False
for t in data.get('tasks', []):
    if t.get('id') == 'MAXCAP-STEP-6':
        t['status'] = 'done' if ok else 'todo'
        t['notes'] = 'job-ok' if ok else 'job-failed'
        found = True
        break
if not found:
    data.setdefault('tasks', []).append({'id': 'MAXCAP-STEP-6', 'title': 'enqueue plan_apply jobs', 'status': 'done' if ok else 'todo', 'notes': 'auto'})

data['ts'] = now
tasks_file.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding='utf-8')

# Append ASCII session status
ss = logs / 'session_status.txt'
with ss.open('a', encoding='ascii', errors='ignore') as f:
    f.write('\nMAXCAP-STEP-6: ' + ('done' if ok else 'failed') + '\n')

# Regenerate ASCII tasks report if available
try:
    from dev.task_tracker_ascii import write_ascii_tasks  # type: ignore
    write_ascii_tasks()
except Exception:
    pass

print('ok' if ok else 'fail')
