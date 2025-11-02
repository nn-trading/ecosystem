# ASCII-only helper: run snapshot-run and update STATUS.md and logs/tasks.json
import os, sys, json, time, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / '.venv' / 'Scripts' / 'python.exe'
if not PY.exists():
    PY = Path(sys.executable)

CLI = ROOT / 'dev' / 'eventlog_cli.py'


def run_snapshot(n: int = 200) -> Path:
    proc = subprocess.run([str(PY), str(CLI), 'snapshot-run', '-n', str(n)], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"snapshot-run failed: {proc.returncode}: {proc.stderr.strip()}")
    lines = [ln.strip() for ln in (proc.stdout or '').splitlines() if ln.strip()]
    if not lines:
        raise SystemExit('snapshot-run produced no output path')
    out = Path(lines[-1].strip())
    if not out.is_absolute():
        out = ROOT / out
    return out


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding='utf-8', errors='ignore'))
    except Exception:
        return {}


def update_status(snapshot_dir: Path) -> None:
    stats = load_json(snapshot_dir / 'stats.json')
    tops = load_json(snapshot_dir / 'top_topics.json') or []
    top_topic = ''
    if isinstance(tops, list) and tops:
        try:
            top_topic = str(tops[0][0])
        except Exception:
            top_topic = ''
    total = stats.get('total')
    # Normalize path for STATUS to relative runs/<ts>
    try:
        rel = snapshot_dir.relative_to(ROOT)
        disp = str(rel).replace('/', '\\')
    except Exception:
        disp = str(snapshot_dir)
    line = f"EventLog: snapshot at {disp} (stats/recent/top_topics); Total events: {total}; Top topic: {top_topic}"
    status_path = ROOT / 'STATUS.md'
    if not status_path.exists():
        return
    lines = status_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    new_lines = []
    replaced = False
    for l in lines:
        if not replaced and l.strip().startswith('EventLog: snapshot at '):
            new_lines.append(line)
            replaced = True
        else:
            new_lines.append(l)
    if not replaced:
        new_lines.append(line)
    status_path.write_text("\n".join(new_lines) + "\n", encoding='ascii', errors='ignore')


def update_tasks() -> None:
    path = ROOT / 'logs' / 'tasks.json'
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8', errors='ignore'))
        else:
            data = {"tasks": []}
    except Exception:
        data = {"tasks": []}
    tasks = list(data.get('tasks') or [])
    found = None
    for t in tasks:
        if isinstance(t, dict) and t.get('id') == 'CORE-03-Snapshot-Spec':
            found = t
            break
    if found is None:
        tasks.append({"id": "CORE-03-Snapshot-Spec", "title": "Snapshot spec: README + index for runs/<ts>", "status": "done", "notes": "eventlog_cli snapshot-run writes README.txt and index.json"})
    else:
        found['status'] = 'done'
        found['title'] = "Snapshot spec: README + index for runs/<ts>"
        found['notes'] = "eventlog_cli snapshot-run writes README.txt and index.json"
    data['tasks'] = tasks
    data['updated_ts'] = int(time.time())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding='ascii', errors='ignore')


def update_next_steps(snapshot_dir: Path) -> None:
    p = ROOT / 'NEXT_STEPS.md'
    ts = time.strftime('%Y%m%d-%H%M%S', time.localtime())
    line = f"{ts} snapshot-run created {snapshot_dir}"
    if p.exists():
        with open(p, 'a', encoding='ascii', errors='ignore') as f:
            f.write(line + '\n')
    else:
        p.write_text(line + '\n', encoding='ascii', errors='ignore')


def git_commit(paths):
    def run(args):
        subprocess.run(args, cwd=str(ROOT), check=False)
    run(['git', 'add'] + [str(p) for p in paths])
    run(['git', 'commit', '-m', 'snapshot: new EventLog run with README/index; STATUS updated; mark CORE-03-Snapshot-Spec done. Co-authored-by: openhands <openhands@all-hands.dev>'])


def main():
    snap = run_snapshot(200)
    update_status(snap)
    update_tasks()
    update_next_steps(snap)
    git_commit([ROOT / 'STATUS.md', ROOT / 'logs' / 'tasks.json', ROOT / 'NEXT_STEPS.md'])
    print(str(snap))

if __name__ == '__main__':
    main()
