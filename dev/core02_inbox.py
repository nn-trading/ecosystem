# dev/core02_inbox.py
from __future__ import annotations
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT/"reports/inbox"
INBOX_TOOLS = ROOT/"reports/inbox_tools"


def loop_once()->int:
    INBOX.mkdir(parents=True, exist_ok=True)
    INBOX_TOOLS.mkdir(parents=True, exist_ok=True)
    n=0
    for p in sorted((ROOT/"specs/generated").glob("*_agent.yaml")):
        q=INBOX/p.name
        if not q.exists(): q.write_text(p.read_text(encoding="utf-8"), encoding="utf-8"); n+=1
    for p in sorted((ROOT/"specs/generated").glob("*_tool.yaml")):
        q=INBOX_TOOLS/p.name
        if not q.exists(): q.write_text(p.read_text(encoding="utf-8"), encoding="utf-8"); n+=1
    return n

def main():
    import sys
    if len(sys.argv)>=2 and sys.argv[1]=="loop":
        while True:
            try: loop_once()
            except Exception: pass
            time.sleep(3)
    else:
        print(loop_once())

if __name__=="__main__": main()
