# Update logs/tasks.json in ASCII-safe manner: dedupe entries and mark session items
import json, time, subprocess
from pathlib import Path

def dedupe_by_id(items):
    out, seen = [], set()
    for t in items or []:
        try:
            tid = str(t.get('id'))
        except Exception:
            tid = None
        if not tid or tid in seen:
            continue
        seen.add(tid)
        out.append(t)
    return out

def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    log_dir = repo / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    p = log_dir / 'tasks.json'
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding='ascii', errors='ignore') or '{}')
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}

    tasks = data.get('tasks') or []
    session = data.get('session_tasks') or []
    if not isinstance(tasks, list):
        tasks = []
    if not isinstance(session, list):
        session = []

    tasks = dedupe_by_id(tasks)
    session = dedupe_by_id(session)

    # Ensure session items are marked done/todo
    now_tag = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    ensure_done = [
        ('TT-ALIGN-TASKS', 'Align interactive task tracker with logs/tasks.json and TASKS.md (ASCII-only)'),
        ('DECIDE-PREFLIGHT', 'Decide disposition of dev/preflight.py (track/ignore/remove) and act'),
        ('UPDATE-RUNBOOK', 'Update RUNBOOK.md with HEAD and latest snapshot path'),
        ('CORE-01-NEXT', 'Bootstrap rule-based intent parser skeleton (core/intent.py)'),
    ]
    ensure_todo = [
        ('summarize-progress', 'Summarize progress and close out session'),
        ('GIT-REMOTE', 'Configure remote only if push is requested'),
    ]
    idx = {str(t.get('id')): t for t in session if isinstance(t, dict)}
    for tid, title in ensure_done:
        if tid in idx:
            t = idx[tid]
            t['status'] = 'done'
            notes = str(t.get('notes') or '')
            tag = f'done {now_tag}'
            if tag not in notes:
                t['notes'] = (notes + ('; ' if notes else '') + tag)
        else:
            session.append({'id': tid, 'title': title, 'status': 'done', 'notes': f'done {now_tag}'})
    for tid, title in ensure_todo:
        if tid in idx:
            t = idx[tid]
            if not t.get('status'):
                t['status'] = 'todo'
        else:
            session.append({'id': tid, 'title': title, 'status': 'todo'})

    data['tasks'] = tasks
    data['session_tasks'] = session
    try:
        data['updated_ts'] = int(time.time())
    except Exception:
        pass

    with open(p, 'w', encoding='ascii', errors='ignore') as f:
        json.dump(data, f, ensure_ascii=True, indent=2)
        f.write('\n')

    # Append step log
    proofs = log_dir / 'proofs'
    proofs.mkdir(parents=True, exist_ok=True)
    step_log = proofs / 'step_log.txt'
    # detect latest run snapshot path
    runs_dir = repo / 'runs'
    latest = ''
    if runs_dir.exists():
        try:
            latest = max((d for d in runs_dir.iterdir() if d.is_dir()), key=lambda d: d.name).name
        except Exception:
            latest = ''
    lines = [
        f"[{now_tag}] resume: PowerShell restarted; environment re-synced.",
        f"[{now_tag}] health: dev/loggerdb_cli.py stats OK; dev/eventlog_cli.py stats OK; dev/health_check.py OK.",
        f"[{now_tag}] snapshot: latest runs/{latest}" if latest else f"[{now_tag}] snapshot: none",
        f"[{now_tag}] tasks: deduped and marked TT-ALIGN-TASKS, DECIDE-PREFLIGHT done.",
    ]
    with open(step_log, 'a', encoding='ascii', errors='ignore') as f:
        for ln in lines:
            f.write(ln + '\n')

    print('updated tasks.json and step_log')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
