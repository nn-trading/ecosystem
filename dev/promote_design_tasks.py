# Promote CORE-01-Design and CORE-03-Design from session_tasks into tasks if missing
import json, time
from pathlib import Path
p=Path('logs/tasks.json')
d=json.loads(p.read_text(encoding='ascii', errors='ignore'))

def index_by_id(lst):
    return {t.get('id'): t for t in lst}

tasks=list(d.get('tasks', []))
session=list(d.get('session_tasks', []))
idx=index_by_id(tasks)
ses_idx=index_by_id(session)
for tid in ('CORE-01-Design','CORE-03-Design'):
    if tid not in idx and tid in ses_idx:
        src=ses_idx[tid]
        tasks.append({k: src[k] for k in ('id','title','status','notes') if k in src})

d['tasks']=tasks
d['updated_ts']=int(time.time())
p.write_text(json.dumps(d, ensure_ascii=True, indent=2)+"\n", encoding='ascii', errors='ignore')
print('promoted')
