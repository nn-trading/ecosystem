import os, sys, glob, json, re

ROOT = os.path.abspath(os.path.dirname(__file__) + os.sep + '..')
LOGS = os.path.join(ROOT, 'logs')
REPORTS = os.path.join(ROOT, 'reports')

patterns = ['error', 'traceback', 'failed', 'exception']
issues = {k: 0 for k in patterns}
files = []
snapshot_ok = False

try:
    # Gather files
    files = sorted(glob.glob(os.path.join(LOGS, 'conf_*.out'))) + \
            sorted(glob.glob(os.path.join(LOGS, 'conf_*.json')))
    snap_json = os.path.join(REPORTS, 'snapshot_validate.json')
    if os.path.exists(snap_json):
        files.append(snap_json)
        try:
            with open(snap_json, 'r', encoding='ascii', errors='ignore') as f:
                data = json.load(f)
            snapshot_ok = bool(data.get('ok', False))
        except Exception:
            snapshot_ok = False

    # Scan files for issue keywords
    for path in files:
        try:
            with open(path, 'r', encoding='ascii', errors='ignore') as f:
                txt = f.read().lower()
            for p in patterns:
                issues[p] += len(re.findall(re.escape(p), txt))
        except Exception:
            # ignore read errors
            pass

    ok = (sum(issues.values()) == 0) and snapshot_ok

    out_json_path = os.path.join(REPORTS, 'conf_summary.json')
    os.makedirs(REPORTS, exist_ok=True)
    with open(out_json_path, 'w', encoding='ascii', errors='ignore') as f:
        json.dump({
            'ok': bool(ok),
            'files_scanned': len(files),
            'issues': issues,
            'snapshot_ok': bool(snapshot_ok)
        }, f, ensure_ascii=True)

    # concise ASCII table
    table_lines = []
    table_lines.append('CONF SUMMARY')
    table_lines.append('files_scanned: %d' % len(files))
    table_lines.append('issues: error=%d, traceback=%d, failed=%d, exception=%d' % (
        issues['error'], issues['traceback'], issues['failed'], issues['exception']))
    table_lines.append('snapshot_ok: %s' % ('true' if snapshot_ok else 'false'))
    table_lines.append('overall_ok: %s' % ('true' if ok else 'false'))

    with open(os.path.join(LOGS, 'conf_summary.out'), 'w', encoding='ascii', errors='ignore') as f:
        f.write('\n'.join(table_lines) + '\n')

    # print JSON path
    sys.stdout.write(out_json_path + '\n')
except SystemExit:
    raise
except Exception as e:
    # Best-effort failure output
    try:
        with open(os.path.join(LOGS, 'conf_summary.out'), 'w', encoding='ascii', errors='ignore') as f:
            f.write('CONF SUMMARY ERROR: %s\n' % (str(e)))
    except Exception:
        pass
    sys.stdout.write(os.path.join(REPORTS, 'conf_summary.json') + '\n')
    sys.exit(0)
