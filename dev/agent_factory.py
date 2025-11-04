# dev/agent_factory.py (ASCII-only)
from __future__ import annotations
import sys, json, os
from pathlib import Path
from core.ascii_writer import write_text_ascii

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT/"reports/inbox"
AGENTS_DIR = ROOT/"agents/generated"


def main():
    INBOX.mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    created=[]
    for p in sorted(INBOX.glob("*_agent.yaml")):
        spec=p.read_text(encoding="utf-8")
        name = p.stem.replace("_agent","")
        out = AGENTS_DIR/f"{name}.txt"
        write_text_ascii(str(out), spec)
        created.append(out.name)
    print(json.dumps({"ok":True, "created": created}))

if __name__=="__main__": main()
