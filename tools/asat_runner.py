from __future__ import annotations
import os, sys, time, json, argparse, hashlib
from typing import Dict, Any, List

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RUNS = os.path.join(REPO, 'runs')

# Lazy imports to avoid cycles

def _commit_hash() -> str:
    try:
        import subprocess
        out = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, stderr=subprocess.DEVNULL)
        return out.decode('ascii', 'ignore').strip()
    except Exception:
        return 'unknown'


def _ts() -> str:
    return time.strftime('%Y%m%d_%H%M%S')


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def run_eval(category: str = '', flt: str = '') -> Dict[str, Any]:
    # Reuse tools/eval_runner to get results in memory
    if REPO not in sys.path:
        sys.path.insert(0, REPO)
    from tools.eval_runner import collect_tasks
    tasks = collect_tasks()
    if category:
        tasks = [t for t in tasks if t.category == category]
    if flt:
        q = flt.lower()
        tasks = [t for t in tasks if (q in t.id.lower() or q in t.name.lower() or q in t.category.lower())]

    passed = failed = errors = 0
    results: List[Dict[str, Any]] = []
    started = time.time()
    for t in tasks:
        rec = t.run()
        results.append(rec)
        if rec['status'] == 'pass':
            passed += 1
        elif rec['status'] == 'fail':
            failed += 1
        else:
            errors += 1
    dur = time.time() - started
    return {
        'total': len(tasks), 'passed': passed, 'failed': failed, 'errors': errors,
        'duration_sec': round(dur, 6), 'results': results
    }


def write_ascii_artifacts(out_dir: str, summary: Dict[str, Any]) -> Dict[str, str]:
    from core.ascii_writer import write_text_ascii, write_jsonl_ascii
    _ensure_dir(out_dir)
    # Report text
    lines = []
    lines.append('--- Acceptance Audit Summary ---')
    lines.append(f"Commit: {summary.get('commit','unknown')}")
    lines.append(f"Tasks: {summary['total']}  Pass: {summary['passed']}  Fail: {summary['failed']}  Error: {summary['errors']}")
    lines.append(f"Duration: {summary['duration_sec']}s")
    # Simple per-category counts
    cats: Dict[str, int] = {}
    for r in summary['results']:
        cats[r['category']] = cats.get(r['category'], 0) + 1
    lines.append('By category: ' + ', '.join(f"{k}={v}" for k,v in sorted(cats.items())))
    report_txt = '\n'.join(lines) + '\n'
    p_report = os.path.join(out_dir, 'report.txt')
    write_text_ascii(p_report, report_txt)

    # Results JSONL (ASCII-safe)
    p_results = os.path.join(out_dir, 'results.jsonl')
    for r in summary['results']:
        write_jsonl_ascii(p_results, r)

    # Summary JSON (single-line summary.json)
    p_summary = os.path.join(out_dir, 'summary.json')
    write_text_ascii(p_summary, json.dumps({k: v for k, v in summary.items() if k != 'results'}, ensure_ascii=True))

    return {'report': p_report, 'results': p_results, 'summary': p_summary}


def main():
    parser = argparse.ArgumentParser(description='Acceptance Audit Runner (ASAT)')
    parser.add_argument('--category', type=str, default='', help='Run only a specific category')
    parser.add_argument('--filter', type=str, default='', help='Substring filter for tasks')
    parser.add_argument('--out', type=str, default='', help='Output directory under runs/<ts>; default auto')
    parser.add_argument('--clean', action='store_true', help='Clean runs directory before writing')
    args = parser.parse_args()

    if args.clean and os.path.exists(RUNS):
        import shutil
        shutil.rmtree(RUNS, ignore_errors=True)

    commit = _commit_hash()
    stamp = _ts()
    out_dir = args.out or os.path.join(RUNS, stamp)
    _ensure_dir(out_dir)

    ev = run_eval(args.category, args.filter)
    ev['commit'] = commit

    paths = write_ascii_artifacts(out_dir, ev)

    print('ASAT completed')
    print('Output directory:', out_dir)
    print('Commit:', commit)
    print('Artifacts:')
    for k, v in paths.items():
        print(f'  {k}: {v}')

if __name__ == '__main__':
    sys.exit(main())
