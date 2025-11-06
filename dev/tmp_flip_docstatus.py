import json, time
from pathlib import Path
p = Path('logs/tasks.json')
d = json.loads(p.read_text(encoding='ascii', errors='ignore'))
d['ts'] = time.strftime('%Y-%m-%d %H:%M:%S')

def _flip(lst):
    ch=False
    for t in lst or []:
        if t.get('id') == 'DOC-STATUS':
            if t.get('status') != 'done':
                t['status'] = 'done'
                ch=True
    return ch

changed=False
if 'tasks' in d:
    changed = _flip(d['tasks']) or changed
if isinstance(d.get('session'), dict) and 'tasks' in d['session']:
    changed = _flip(d['session']['tasks']) or changed
if 'session_tasks' in d:
    changed = _flip(d['session_tasks']) or changed

if changed:
    p.write_text(json.dumps(d, ensure_ascii=True, separators=(',',':'))+'\n', encoding='ascii', errors='ignore')
print('updated' if changed else 'nochange')
