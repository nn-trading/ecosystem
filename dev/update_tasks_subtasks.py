# ASCII-only updater for logs/tasks.json CORE-01/03 subtasks
import json, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = ROOT / 'logs' / 'tasks.json'

NEW_TASKS = [
    ("CORE-01-Design-Outline", "Design outline for intent and replanning", "todo", "Outline components: parser, planner, executor, evaluator, replan loop"),
    ("CORE-01-Parser-Impl", "Implement simple intent parser", "todo", "Heuristics for goal/constraints/success; baseline exists in core/intent.py"),
    ("CORE-01-Planner-API", "Define planner API to produce steps", "todo", "Planner to emit WorkerAgent-compatible steps"),
    ("CORE-01-Evaluator-Replan", "Evaluator + replan loop", "todo", "Define success checks and triggers to replan"),
    ("CORE-03-Schema-Finalize", "Finalize LoggerDB schema and compat", "todo", "Ensure FTS triggers and mirror DB compatibility"),
    ("CORE-03-CLI-Converge", "Converge EventLog CLI commands", "todo", "stats, recent, search, snapshot-run"),
    ("CORE-03-Snapshot-Spec", "Snapshot spec: README + index for runs/<ts>", "todo", "eventlog_cli snapshot-run to emit README.txt and index.json"),
    ("CORE-03-Search-Escapes", "Search escapes and fallback", "todo", "FTS with quoted retry and LIKE fallback for specials")
]


def load_tasks(path: Path) -> dict:
    if not path.exists():
        return {"tasks": [], "session_tasks": []}
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            return json.load(f)
        except Exception:
            return {"tasks": [], "session_tasks": []}


def ensure_task(tasks: list, tid: str, title: str, status: str, notes: str) -> list:
    found = None
    for t in tasks:
        if isinstance(t, dict) and t.get('id') == tid:
            found = t
            break
    if found is None:
        obj = {"id": tid, "title": title, "status": status}
        if notes:
            obj["notes"] = notes
        tasks.append(obj)
    else:
        found["title"] = title
        found["status"] = status
        if notes:
            found["notes"] = notes
    return tasks


def main():
    data = load_tasks(TASKS_PATH)
    tasks = list(data.get('tasks') or [])
    for tid, title, status, notes in NEW_TASKS:
        tasks = ensure_task(tasks, tid, title, status, notes)
    data['tasks'] = tasks
    data['updated_ts'] = int(time.time())
    TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_PATH, 'w', encoding='ascii', errors='ignore') as f:
        json.dump(data, f, ensure_ascii=True, indent=4)
        f.write("\n")

if __name__ == '__main__':
    main()
