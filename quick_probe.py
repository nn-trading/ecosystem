# C:\bots\ecosys\quick_probe.py
import os, sys, json, glob, sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent
LOGS = REPO / 'logs'
WS_LOGS = REPO / 'workspace' / 'logs'

results = []

# PID files
for name in ('ecosys_pid.txt','headless_pid.txt'):
    p = LOGS / name
    results.append({'check':'pid_exists','name':name,'exists':p.exists()})
    if p.exists():
        try:
            txt = p.read_text(encoding='ascii', errors='ignore').strip()
            results.append({'check':'pid_isdigit','name':name,'ok':txt.isdigit(),'value':txt})
        except Exception as e:
            results.append({'check':'pid_read_err','name':name,'err':str(e)})

# TASKS.md ASCII-only
md = REPO / 'TASKS.md'
results.append({'check':'tasks_md_exists','exists':md.exists()})
if md.exists():
    try:
        data = md.read_bytes()
        ascii_only = all(b < 128 for b in data)
        results.append({'check':'tasks_md_ascii','ok':ascii_only})
    except Exception as e:
        results.append({'check':'tasks_md_read_err','err':str(e)})

# Orphan backups cleanup
for d in (LOGS, WS_LOGS):
    try:
        patt = str(d / 'events_backup_*.jsonl')
        leftovers = glob.glob(patt)
        results.append({'check':'orphan_backups_clean', 'dir':str(d), 'ok':len(leftovers)==0, 'leftovers': [os.path.basename(x) for x in leftovers]})
    except Exception as e:
        results.append({'check':'orphan_backups_err','dir':str(d),'err':str(e)})

# Memory DB presence
mem_db = os.environ.get('ECOSYS_MEMORY_DB', r'C:\\bots\\data\\memory.db')
try:
    p = Path(mem_db)
    results.append({'check':'memory_db_path', 'path':str(p), 'exists':p.exists()})
    if p.exists():
        try:
            con = sqlite3.connect(str(p))
            cur = con.cursor()
            cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
            tables = [r[0] for r in cur.fetchall()]
            results.append({'check':'memory_db_tables','tables':tables})
            con.close()
        except Exception as e:
            results.append({'check':'memory_db_open_err','err':str(e)})
except Exception as e:
    results.append({'check':'memory_db_err','err':str(e)})

print(json.dumps(results, indent=2))
