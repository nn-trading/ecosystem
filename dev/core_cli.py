# dev/core_cli.py
import sys, subprocess, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = str((ROOT/".venv/Scripts/python.exe").resolve())
def run(args): return subprocess.run(args, capture_output=True, text=True)
def status():
    p = ROOT/"reports/SELFHEAL_STATUS.txt"
    print(p.read_text(encoding="utf-8")[:6000] if p.exists() else '{"note":"no selfheal status yet"}')
def smoke():
    a=run([PY,"dev/core01.py"]); b=run([PY,"dev/core03_desktop.py"]) 
    print("CORE-01 rc",a.returncode); print(a.stdout); print(a.stderr)
    print("CORE-03 rc",b.returncode); print(b.stdout); print(b.stderr)

def main():
    cmd = (sys.argv[1] if len(sys.argv)>1 else "smoke").lower()
    if cmd=="status": status()
    elif cmd=="smoke": smoke()
    else: print("Usage: python dev\\core_cli.py [status|smoke]")
if __name__=="__main__": main()
