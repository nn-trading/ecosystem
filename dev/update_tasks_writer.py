import json, os, time

TASKS_JSON = os.path.join('logs', 'tasks.json')

SESSION_PLAN = [
    {"id": "02-setup-run", "title": "Environment verified; pytest successful (30 passed, 1 skipped, 3 warnings)", "status": "done"},
    {"id": "03-clean-strays", "title": "Removed reserved-name stray file CON using device path", "status": "done"},
    {"id": "04-db-unify", "title": "Prefer ECOSYS_MEMORY_DB with default var\\events.db", "status": "done"},
    {"id": "05-tasks-persist", "title": "Adopt ASCII-only logs/tasks.json writer; stop sessions/TASKS.md writes", "status": "done", "notes": "Using Python ensure_ascii writer"},
    {"id": "06-runbook-update", "title": "RUNBOOK.md updated and committed to reflect HEAD and test summary", "status": "done"},
    {"id": "07-asat-script", "title": "Commit dev\\run_asat.ps1 with header/usage", "status": "done"},
    {"id": "08-next-actions", "title": "Prioritize CORE-01 and CORE-03 after tasks-persist decision", "status": "in_progress"},
]

def read_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def write_json_ascii(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='ascii', errors='backslashreplace') as f:
        json.dump(data, f, ensure_ascii=True, indent=2)
        f.write('\n')
    os.replace(tmp, path)

def upsert(lst, item):
    for i, x in enumerate(lst):
        if isinstance(x, dict) and x.get('id') == item.get('id'):
            lst[i] = {**x, **item}
            return
    lst.append(item)

if __name__ == '__main__':
    data = read_json(TASKS_JSON)
    if not isinstance(data, dict):
        data = {"tasks": []}
    session_tasks = data.get('session_tasks') or []
    for it in SESSION_PLAN:
        upsert(session_tasks, it)
    data['session_tasks'] = session_tasks
    data['updated_ts'] = int(time.time())
    write_json_ascii(TASKS_JSON, data)
    print('Wrote logs/tasks.json with', len(session_tasks), 'session tasks')
