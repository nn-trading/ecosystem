# dev/core_cli.py
import sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = str((ROOT/".venv/Scripts/python.exe").resolve())
def run(a): return subprocess.run(a, capture_output=True, text=True)
def status():
    p = ROOT/"reports/SELFHEAL_STATUS.txt"
    print(p.read_text(encoding="utf-8")[:6000] if p.exists() else '{"note":"no selfheal status yet"}')
def smoke():
    a=run([PY,"dev/core01.py"]); b=run([PY,"dev/core03_desktop.py"]) 
    print("CORE-01 rc",a.returncode); print(a.stdout); print(a.stderr)
    print("CORE-03 rc",b.returncode); print(b.stdout); print(b.stderr)

def mt5():
    c=run([PY,"dev/core04_mt5.py"]) 
    print("CORE-04 rc",c.returncode); print(c.stdout); print(c.stderr)

def main():
    cmd=(sys.argv[1] if len(sys.argv)>1 else "smoke").lower()
    if cmd=="status": status()
    elif cmd=="smoke": smoke()
    elif cmd=="mt5": mt5()
    else: print("Usage: python dev\\core_cli.py [status|smoke|mt5]")
if __name__=="__main__": main()
