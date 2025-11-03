# dev/db_cli.py (ASCII-only)
import sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = str((ROOT/".venv/Scripts/python.exe").resolve())

def run(args):
    return subprocess.run(args, capture_output=True, text=True)

def main():
    cmd = (sys.argv[1] if len(sys.argv)>1 else "health").lower()
    if cmd not in ("health","stats","vacuum","snapshot"):
        print("Usage: python dev\\db_cli.py [health|stats|vacuum|snapshot]")
        return
    r = run([PY,"dev/db_unify.py",cmd])
    print(r.stdout)

if __name__=="__main__":
    main()
