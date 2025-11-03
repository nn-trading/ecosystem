import os, sys, json, subprocess

REPO = r"C:\bots\ecosys"
PROOFS_DIR = os.path.join(REPO, 'logs', 'proofs')
os.makedirs(PROOFS_DIR, exist_ok=True)

PY = sys.executable

def run(args):
    p = subprocess.run([PY] + args, cwd=REPO, capture_output=True, text=True)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()

art = {}
rc, out, err = run(['dev/loggerdb_cli.py', 'stats'])
art['loggerdb_stats'] = out
rc, out, err = run(['dev/loggerdb_cli.py', 'recent', '-n', '5'])
art['loggerdb_recent'] = out
rc, out, err = run(['dev/loggerdb_cli.py', 'search', 'system/heartbeat', '-n', '5'])
art['loggerdb_search_heartbeat'] = out
rc, out, err = run(['dev/loggerdb_cli.py', 'artifacts', '-n', '5'])
art['loggerdb_artifacts'] = out
rc, out, err = run(['dev/eventlog_cli.py', 'stats'])
art['eventlog_stats'] = out
rc, out, err = run(['dev/eventlog_cli.py', 'recent', '-n', '5'])
art['eventlog_recent'] = out
rc, out, err = run(['dev/eventlog_cli.py', 'search', 'system/heartbeat', '-n', '5'])
art['eventlog_search_heartbeat'] = out

path = os.path.join(PROOFS_DIR, 'loggerdb_cli_smoke.json')
with open(path, 'w', encoding='ascii', errors='ignore') as f:
    json.dump(art, f, ensure_ascii=True, indent=2)
    f.write('\n')
print(path)
