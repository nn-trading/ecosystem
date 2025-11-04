import json, io, time
from pathlib import Path

p = Path('logs/tasks.json')
try:
    with io.open(p, 'r', encoding='ascii', errors='ignore') as f:
        data = json.load(f)
except Exception:
    data = {"tasks": [], "session_tasks": []}

def set_status(tasks, tid, status, note=None):
    found = None
    for t in tasks:
        if isinstance(t, dict) and t.get('id') == tid:
            found = t
            break
    if found is None:
        obj = {"id": tid, "title": tid, "status": status}
        if note:
            obj["notes"] = note
        tasks.append(obj)
    else:
        found["status"] = status
        if note:
            old = str(found.get("notes") or "")
            if note not in old:
                found["notes"] = (old + (" " if old else "") + note).strip()

tasks = list(data.get("tasks") or [])

# Update only items confirmed implemented
set_status(tasks, "CORE-01-Parser-Impl", "done", "parse_intent implemented in core/intent.py; tests cover in tests/test_intent.py")

# Persist back
data["tasks"] = tasks
ses = list(data.get("session_tasks") or [])
ses.append({"id": f"SESSION-{int(time.time())}", "title": "Resume: tasks sync; health; snapshot", "status": "done", "notes": "ascii"})
data["session_tasks"] = ses
data["updated_ts"] = int(time.time())

p.parent.mkdir(parents=True, exist_ok=True)
with io.open(p, 'w', encoding='ascii', errors='ignore') as f:
    json.dump(data, f, ensure_ascii=True, indent=2)
    f.write("\n")

print("updated tasks.json")
