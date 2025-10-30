import json, time
from pathlib import Path

p = Path('logs/tasks.json')
with open(p, 'r', encoding='ascii', errors='ignore') as f:
    data = json.load(f)

def upsert(lst, item):
    for i, it in enumerate(lst):
        if it.get('id') == item['id']:
            merged = dict(it)
            for k, v in item.items():
                if v is not None:
                    merged[k] = v
            lst[i] = merged
            return
    lst.append(item)

# Ensure CORE-03 notes mention FTS legacy compat
for it in data.get('tasks', []):
    if it.get('id') == 'CORE-03':
        notes = it.get('notes') or ''
        add = 'FTS triggers legacy-compatible via _ensure_fts_triggers_compat(); LIKE fallback preserved.'
        if add not in notes:
            it['notes'] = (notes + (' ' if notes else '') + add).strip()
        break

ses = list(data.get('session_tasks', []))
upsert(ses, {"id":"CORE-03-CLI", "title":"LoggerDB CLI basics: stats/recent/search", "status":"done"})
upsert(ses, {"id":"CORE-03-SNAPSHOT", "title":"LoggerDB snapshot-run to runs/<ts>/", "status":"done"})
upsert(ses, {"id":"CORE-03-CLI-FIX-TABS", "title":"CLI output spacing/tabs normalization", "status":"done"})
upsert(ses, {"id":"ASCII-02-SYNC", "title":"Sync logs/tasks.json with current state (ASCII-only)", "status":"done", "notes":"Updated with CORE-03 notes and session items"})
upsert(ses, {"id":"RUNBOOK-Refresh", "title":"Refresh RUNBOOK with branch/HEAD and snapshot path", "status":"done", "notes":"Branch feature/loggerdb-cli; HEAD 4e400f1; snapshot runs\\20251030_112053; FTS/LIKE documented"})

data['session_tasks'] = ses

data['updated_ts'] = int(time.time())
with open(p, 'w', encoding='ascii', errors='ignore') as f:
    json.dump(data, f, ensure_ascii=True, indent=2)
    f.write('\n')
print('updated tasks.json')
