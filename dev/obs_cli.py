# dev/obs_cli.py (ASCII-only)
import sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = str((ROOT/".venv/Scripts/python.exe").resolve())
EV = ROOT/"dev/eventlog_cli.py"  # optional existing tool

def _call(args):
    return subprocess.run(args, capture_output=True, text=True)


def main():
    if not EV.exists():
        print('{"ok":false,"error":"eventlog_cli.py not found"}')
        return
    if len(sys.argv)<2:
        print("Usage: python dev\\obs_cli.py <stats|recent|search|tail> [args]")
        return
    cmd = sys.argv[1].lower()
    if cmd=="stats":
        r=_call([PY,str(EV),"stats"]); print(r.stdout)
    elif cmd=="recent":
        n = sys.argv[2] if len(sys.argv)>2 else "25"
        r=_call([PY,str(EV),"recent","-n",n]); print(r.stdout)
    elif cmd=="search":
        term = sys.argv[2] if len(sys.argv)>2 else "error"
        n    = sys.argv[3] if len(sys.argv)>3 else "50"
        r=_call([PY,str(EV),"search",term,"-n",n]); print(r.stdout)
    elif cmd=="tail":
        n = sys.argv[2] if len(sys.argv)>2 else "200"
        r=_call([PY,str(EV),"tail","-n",n]); print(r.stdout)
    else:
        print("Usage: python dev\\obs_cli.py <stats|recent|search|tail>")

if __name__=="__main__":
    main()
