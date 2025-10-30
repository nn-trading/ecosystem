# C:\bots\ecosys\quick_probe.py
import os, sys, json, glob, sqlite3, time, hashlib, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent
LOGS = REPO / 'logs'
WS_LOGS = REPO / 'workspace' / 'logs'

results = []

# PID files + live verification
try:
    import psutil  # type: ignore
except Exception:
    psutil = None  # runtime optional

for name in ('ecosys_pid.txt','headless_pid.txt'):
    p = LOGS / name
    results.append({'check':'pid_exists','name':name,'exists':p.exists()})
    if p.exists():
        try:
            txt = p.read_text(encoding='ascii', errors='ignore').strip()
            isdig = txt.isdigit()
            live = False
            if isdig and psutil is not None:
                try:
                    live = psutil.pid_exists(int(txt))
                except Exception:
                    live = False
            results.append({'check':'pid_info','name':name,'isdigit':isdig,'value':txt,'live':live})
        except Exception as e:
            results.append({'check':'pid_read_err','name':name,'err':str(e)})

# TASKS.md ASCII-only
md = REPO / 'TASKS.md'
results.append({'check':'tasks_md_exists','exists':md.exists()})
if md.exists():
    try:
        data = md.read_bytes()
        ascii_only = all(b < 128 for b in data)
        results.append({'check':'tasks_md_ascii','ok':ascii_only})
    except Exception as e:
        results.append({'check':'tasks_md_read_err','err':str(e)})

# Orphan backups cleanup
for d in (LOGS, WS_LOGS):
    try:
        patt = str(d / 'events_backup_*.jsonl')
        leftovers = glob.glob(patt)
        results.append({'check':'orphan_backups_clean', 'dir':str(d), 'ok':len(leftovers)==0, 'leftovers': [os.path.basename(x) for x in leftovers]})
    except Exception as e:
        results.append({'check':'orphan_backups_err','dir':str(d),'err':str(e)})

# Memory DB presence
mem_db = os.environ.get('ECOSYS_MEMORY_DB', str(REPO / 'var' / 'events.db'))
try:
    p = Path(mem_db)
    results.append({'check':'memory_db_path', 'path':str(p), 'exists':p.exists()})
    if p.exists():
        try:
            con = sqlite3.connect(str(p))
            cur = con.cursor()
            cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
            tables = [r[0] for r in cur.fetchall()]
            results.append({'check':'memory_db_tables','tables':tables})
            con.close()
        except Exception as e:
            results.append({'check':'memory_db_open_err','err':str(e)})
except Exception as e:
    results.append({'check':'memory_db_err','err':str(e)})

# Repo inventory (ASCII-safe) and write logs/repo_state.json

def _sha1_bytes(data: bytes) -> str:
    try:
        return hashlib.sha1(data).hexdigest()
    except Exception:
        return ''

def _inventory_repo(root: Path) -> dict:
    ex_dirs = {'.git', '.venv', 'workspace', 'logs', '__pycache__'}
    by_ext: dict[str,int] = {}
    files_list: list[dict] = []
    total_bytes = 0
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in ex_dirs]
        for fn in filenames:
            try:
                rp = Path(dirpath) / fn
                rel = str(rp.relative_to(root))
                ext = (rp.suffix or '').lstrip('.').lower()
                by_ext[ext] = by_ext.get(ext, 0) + 1
                sz = rp.stat().st_size
                total_bytes += sz
                count += 1
                entry = {'path': rel, 'size': sz}
                # hash small files only (<=256KB)
                if sz <= 262144:
                    try:
                        entry['sha1'] = _sha1_bytes(rp.read_bytes())
                    except Exception:
                        pass
                files_list.append(entry)
            except Exception:
                pass
    summary = {
        'generated_ts': time.time(),
        'root': str(root),
        'files_total': count,
        'bytes_total': total_bytes,
        'by_ext': by_ext,
    }
    return {'summary': summary, 'files': files_list}


# Git info (branch/commit/clean)
def _git_info(root: Path) -> dict:
    info = {"branch": "", "commit": "", "clean": True}
    try:
        def run(args: list[str]) -> str:
            return subprocess.check_output(args, cwd=str(root), stderr=subprocess.DEVNULL).decode("ascii", "ignore").strip()
        commit = run(["git", "rev-parse", "--short", "HEAD"]) or ""
        branch = run(["git", "branch", "--show-current"]) or ""
        status = run(["git", "status", "--porcelain=v1"]) or ""
        info["branch"], info["commit"], info["clean"] = branch, commit, (status == "")
    except Exception:
        pass
    return info

try:
    inv = _inventory_repo(REPO)
    out_path = LOGS / 'repo_state.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gi = _git_info(REPO)
    tmp = str(out_path) + '.tmp'
    with open(tmp, 'w', encoding='ascii', errors='backslashreplace') as f:
        json.dump({'root': str(REPO), 'git': gi, **inv}, f, ensure_ascii=True)
        f.write('\n')
    os.replace(tmp, out_path)
    results.append({'check':'repo_state_written','path':str(out_path),'files':inv['summary']['files_total'], 'branch': gi.get('branch',''), 'commit': gi.get('commit',''), 'clean': gi.get('clean', True)})
except Exception as e:
    results.append({'check':'repo_state_err','err':str(e)})

print(json.dumps(results, ensure_ascii=True))
