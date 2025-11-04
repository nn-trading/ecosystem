# dev/factory_cli.py
import sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable or "python"

def main():
    if len(sys.argv)<2:
        print("Usage: python dev\\factory_cli.py [agents|tools]"); return
    cmd = sys.argv[1]
    if cmd=="agents":
        subprocess.run([PY, "dev/agent_factory.py"], cwd=str(ROOT))
    elif cmd=="tools":
        subprocess.run([PY, "dev/tools_builder.py"], cwd=str(ROOT))
    else:
        print("unknown"); return

if __name__=="__main__": main()
