# dev/tools_builder.py (ASCII-only)
from __future__ import annotations
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT/"reports/inbox_tools"
TOOLS_DIR = ROOT/"tools/generated"


def main():
    INBOX.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    created=[]
    for p in sorted(INBOX.glob("*_tool.yaml")):
        spec=p.read_text(encoding="utf-8")
        name = p.stem.replace("_tool","")
        out = TOOLS_DIR/f"{name}.txt"
        out.write_text(spec, encoding="utf-8")
        created.append(out.name)
    print(json.dumps({"ok":True, "created": created}))

if __name__=="__main__": main()
