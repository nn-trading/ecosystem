import os, sys, json, subprocess

# Ensure repo root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.memory import Memory


def check_headless_alive(pid_path: str) -> bool:
    try:
        with open(pid_path, 'r', encoding='utf-8', errors='ignore') as f:
            pid_txt = (f.read() or '').strip().splitlines()[0].strip()
        pid = int(pid_txt)
    except Exception:
        return False
    # Use PowerShell to check process existence to avoid external deps
    try:
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-Command', f"try { '{' } Get-Process -Id {pid} -ErrorAction Stop | Out-Null; exit 0 { '}' } catch { '{' } exit 1 { '}' }"
        ]
        rc = subprocess.run(cmd).returncode
        return rc == 0
    except Exception:
        return False


def main():
    n = int(os.environ.get('PROBE_TAIL', '2000'))
    mem = Memory()
    events = mem.tail_events(n)
    hb = [e for e in events if e.get('topic') == 'system/heartbeat']
    hl = [e for e in events if e.get('topic') == 'system/health']

    # Headless PID status
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    pid_path = os.path.join(root, 'logs', 'headless_pid.txt')
    alive = check_headless_alive(pid_path) if os.path.exists(pid_path) else False

    out = {
        'tail_n': n,
        'heartbeat_count': len(hb),
        'health_count': len(hl),
        'heartbeat_tail': hb[-3:],
        'health_tail': hl[-3:],
        'headless_pid_alive': alive,
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
