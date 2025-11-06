import json, time, re
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
logs = repo / 'logs'
status_path = repo / 'dev' / 'STATUS.md'
steps_path = logs / 'steps.log'

def rj(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='ascii', errors='ignore') or '{}')
    except Exception:
        return default

estats = rj(logs / 'eventlog_stats.json', {}) or {}
erecent = rj(logs / 'eventlog_recent.json', []) or []
edb1 = rj(logs / 'eventlog_db_path.json', {}) or {}
edb2 = rj(logs / 'eventlog_dbpath.json', {}) or {}
edb = str(edb1.get('db_path') or edb2.get('db_path') or '')

lstats = rj(logs / 'loggerdb_stats.json', {}) or {}
lrecent = rj(logs / 'loggerdb_recent.json', []) or []
ladb1 = rj(logs / 'loggerdb_dbpath.json', {}) or {}
ladb = str(ladb1.get('db_path') or '')
larts = rj(logs / 'loggerdb_artifacts.json', []) or []

rdir = repo / 'runs'
latest_ts = ''
if rdir.exists():
    try:
        names = [d.name for d in rdir.iterdir() if d.is_dir() and re.match(r'^\d{8}-\d{6}$', d.name)]
        if names:
            latest_ts = sorted(names)[-1]
    except Exception:
        latest_ts = ''

now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
lines = []
lines.append('')
lines.append(f'RC update {now}')
lines.append(f'- EventLog: total {estats.get("total")} rollups {estats.get("rollups")} fts={bool(estats.get("fts"))} db={edb}')
lines.append(f'- LoggerDB: events {lstats.get("events")} artifacts {lstats.get("artifacts")} fts={bool(lstats.get("fts"))} db={ladb}')
if latest_ts:
    lines.append(f'- Latest snapshot: runs/{latest_ts}')
else:
    lines.append('- Latest snapshot: none')
lines.append('- Captures:')
lines.append('  - logs/eventlog_stats.json; logs/eventlog_recent.json; logs/eventlog_db_path.json')
lines.append('  - logs/loggerdb_stats.json; logs/loggerdb_recent.json; logs/loggerdb_artifacts.json; logs/loggerdb_dbpath.json')

status_path.parent.mkdir(parents=True, exist_ok=True)
with open(status_path, 'a', encoding='ascii', errors='ignore') as f:
    f.write('\n'.join(lines) + '\n')

# tasks update
p = logs / 'tasks.json'
data = {}
if p.exists():
    try:
        data = json.loads(p.read_text(encoding='ascii', errors='ignore') or '{}')
    except Exception:
        data = {}
if not isinstance(data, dict):
    data = {}
session = data.get('session_tasks') or []
if not isinstance(session, list):
    session = []

def upsert(tid, title, status, notes=None):
    found = None
    for t in session:
        if isinstance(t, dict) and str(t.get('id')) == tid:
            found = t
            break
    if found is None:
        found = {'id': tid, 'title': title, 'status': status}
        if notes:
            found['notes'] = notes
        session.append(found)
        return
    if title and not found.get('title'):
        found['title'] = title
    if status:
        found['status'] = status
    if notes:
        prev = str(found.get('notes') or '')
        found['notes'] = (prev + ('; ' if prev else '') + notes)

upsert('audit','Audit workspace and git state','in_progress', None)
upsert('eventlog-cli','Capture EventLog stats/recent/db-path','done', f'done {now}')
upsert('loggerdb-cli','Capture LoggerDB stats/recent/artifacts/db-path','done', f'done {now}')
upsert('persist-tasks','Persist tasks via update_tasks_ascii.py and task_tracker_ascii.py','todo', None)
upsert('status-update','Update dev/STATUS.md with latest CLI stats and snapshot','done', f'updated {now}')
upsert('next-milestone','Select next milestone','todo', 'recommend CORE-03 verification')
upsert('step-log','Append step markers to logs/steps.log','in_progress', f'cli captures recorded {now}')
upsert('context','Reconstruct from code/docs','todo', None)
upsert('resume','Execute next actionable milestone','todo', None)
upsert('log','Step logs mechanism; persistent updates','in_progress', None)

data['session_tasks'] = session
try:
    data['ts'] = now
    data['updated_ts'] = int(time.time())
except Exception:
    pass
with open(p, 'w', encoding='ascii', errors='ignore') as f:
    json.dump(data, f, ensure_ascii=True, indent=2)
    f.write('\n')

# steps log
step_lines = [
    f'[{now}] eventlog-cli: wrote stats/recent/db-path',
    f'[{now}] loggerdb-cli: wrote stats/recent/artifacts/db-path',
    f'[{now}] status-update: STATUS.md updated with CLI stats and snapshot',
]
with open(steps_path, 'a', encoding='ascii', errors='ignore') as f:
    for ln in step_lines:
        f.write(ln + '\n')

print('session update ok')
