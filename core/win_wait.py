import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS_HELPER = ROOT / 'dev' / 'win_wait.ps1'

def wait_title_contains(substring: str, timeout_sec: int = 15, poll_ms: int = 200) -> dict:
    if not PS_HELPER.exists():
        return {"ok": False, "error": f"missing helper: {PS_HELPER}"}
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(PS_HELPER),
        "-Substring", substring,
        "-TimeoutSec", str(timeout_sec),
        "-PollMs", str(poll_ms),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        try:
            return json.loads(e.output.strip())
        except Exception:
            return {"ok": False, "error": "powershell failed", "output": e.output}
    out = out.strip()
    last = out.splitlines()[-1]
    try:
        return json.loads(last)
    except Exception:
        return {"ok": False, "error": "non-json output", "output": out}

if __name__ == '__main__':
    sub = sys.argv[1] if len(sys.argv) > 1 else 'Notepad'
    t   = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    p   = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    print(json.dumps(wait_title_contains(sub, t, p)))
