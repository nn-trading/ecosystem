import os, sys, time, json, subprocess, shutil

ROOT = os.path.abspath(os.path.dirname(__file__) + os.sep + '..')
PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
START = os.path.join(ROOT, 'start.ps1')
OBS = os.path.join(ROOT, 'dev', 'obs_cli.py')
PLANNER = os.path.join(ROOT, 'dev', 'core02_planner.py')
CHATOPS = os.path.join(ROOT, 'dev', 'chatops_cli.py')
SUM = os.path.join(ROOT, 'dev', 'chat_summarizer.py')

CYCLES = 5
DELAY = 6

def run_cmd(cmd):
    try:
        t0 = time.time()
        cp = subprocess.run(cmd, capture_output=True, text=True, encoding='ascii', errors='ignore')
        dt = time.time() - t0
        return cp.returncode, cp.stdout, cp.stderr, dt
    except Exception as e:
        return 1, '', str(e), 0.0

def ps_stop():
    return run_cmd(['powershell', '-NoProfile', '-File', START, '-Stop', '1'])

def ps_start_bg():
    return run_cmd(['powershell', '-NoProfile', '-File', START, '-Headless', '1', '-Background', '1', '-EnsureVenv', '1', '-EnsureDeps', '0', '-RunPytest', '0', '-HeartbeatSec', '2', '-HealthSec', '2'])

def enqueue(msg):
    return run_cmd([PY, CHATOPS, msg])

def apply():
    return run_cmd([PY, PLANNER, 'apply'])

def heartbeats_ok():
    code, out, err, dt = run_cmd([PY, OBS, 'log-recent', '10'])
    ok = ('system/heartbeat' in out)
    return ok, code, out, err, dt

def rollup():
    return run_cmd([PY, SUM])

def main():
    cycles = CYCLES
    delay = DELAY
    if len(sys.argv) >= 2:
        try:
            cycles = int(sys.argv[1])
        except Exception:
            pass
    if len(sys.argv) >= 3:
        try:
            delay = int(sys.argv[2])
        except Exception:
            pass

    ts = time.strftime('%Y%m%d_%H%M%S')
    out_dir = os.path.join(ROOT, 'runs', f'conf_stress_{ts}')
    os.makedirs(out_dir, exist_ok=True)

    metrics = {
        'cycles': cycles,
        'delay_sec': delay,
        'results': []
    }

    for i in range(1, cycles+1):
        entry = {'cycle': i}
        time.sleep(1)
        entry['stop'] = run_cmd(['powershell','-NoProfile','-File', START, '-Stop','1'])[0]
        time.sleep(1)
        entry['start_bg'] = run_cmd(['powershell','-NoProfile','-File', START, '-Headless','1','-Background','1','-EnsureVenv','1','-EnsureDeps','0','-RunPytest','0','-HeartbeatSec','2','-HealthSec','2'])[0]
        time.sleep(1)
        entry['enqueue'] = enqueue(f'Health ping cycle {i}')[0]
        time.sleep(1)
        entry['apply'] = apply()[0]
        time.sleep(1)
        hb_ok, hb_code, hb_out, hb_err, hb_dt = heartbeats_ok()
        entry['heartbeat_ok'] = bool(hb_ok)
        entry['heartbeat_rc'] = hb_code
        entry['heartbeat_dt'] = hb_dt
        entry['rollup'] = rollup()[0]
        metrics['results'].append(entry)
        time.sleep(delay)

    all_ok = all(r.get('heartbeat_ok') for r in metrics['results'])
    metrics['all_ok'] = bool(all_ok)

    snap_path = os.path.join(out_dir, 'SNAPSHOT.txt')
    with open(snap_path, 'w', encoding='ascii', errors='ignore') as f:
        f.write('conf_stress %s\n' % ts)
        f.write('cycles=%d delay_sec=%d\n' % (cycles, delay))
        for r in metrics['results']:
            f.write('cycle %d: hb_ok=%s apply_rc=%d rollup_rc=%d\n' % (
                r['cycle'], 'true' if r['heartbeat_ok'] else 'false', r.get('apply', -1), r.get('rollup', -1)))
        f.write('PASS\n' if all_ok else 'FAIL\n')

    with open(os.path.join(out_dir, 'metrics.json'), 'w', encoding='ascii', errors='ignore') as f:
        json.dump(metrics, f, ensure_ascii=True)

    sys.stdout.write(os.path.join(out_dir, 'metrics.json') + '\n')

if __name__ == '__main__':
    main()
