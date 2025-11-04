import json, os, time
root = r'C:\bots\ecosys'
logs = os.path.join(root, 'logs')
os.makedirs(logs, exist_ok=True)
snapshot = {
  'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
  'tasks': [
    {'id':'CTX-01','title':'Resume context','status':'done','notes':'context read; smoke/test verified'},
    {'id':'SMOKE-12','title':'12s smoke','status':'done','notes':'foreground run OK'},
    {'id':'TEST-ALL','title':'pytest all','status':'done','notes':'34 passed, 1 skipped'},
    {'id':'CORE-01','title':'Brain intent and replanning','status':'todo','notes':'wire loops per core.yaml'},
    {'id':'CORE-03','title':'Logger/Memory schema and search','status':'todo','notes':'confirm FTS+LIKE and escaping'},
    {'id':'ASCII-01','title':'ASCII-safe writer','status':'in_progress','notes':'scan writers; fix non-ascii outputs'},
    {'id':'DOC-Update','title':'Update docs','status':'todo','notes':'ASCII only'},
    {'id':'DB-UNIFY','title':'Unified DB path','status':'in_progress','notes':'env var set; health reports present'}
  ]
}
with open(os.path.join(logs,'tasks.json'), 'w', encoding='utf-8') as f:
    json.dump(snapshot, f, ensure_ascii=True, indent=2)
print('wrote logs/tasks.json')
