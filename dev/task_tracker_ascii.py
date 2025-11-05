# dev/task_tracker_ascii.py
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TASKS=ROOT/"logs/tasks.json"
OUT1=ROOT/"reports/TASKS_ASCII.md"

def to_ascii(s:str)->str: return s.encode("ascii","ignore").decode("ascii")
def safe(obj): return to_ascii(json.dumps(obj, ensure_ascii=True, indent=2))

def write_ascii_tasks():
    data={}
    if TASKS.exists():
        try: data=json.loads(TASKS.read_text(encoding="utf-8",errors="ignore"))
        except Exception: data={}
    globs=data.get("tasks") or data.get("global_tasks") or {}
    sess =data.get("session_tasks") or []
    lines=[]
    lines.append("# TASKS (ASCII)")
    lines.append("## Global")
    if isinstance(globs, dict):
        for k,v in globs.items():
            status=v.get("status") if isinstance(v,dict) else v
            lines.append(f"- {k}: {status}")
    elif isinstance(globs, list):
        for x in globs: lines.append(f"- {x}")
    lines.append("")
    lines.append("## Session")
    for x in sess:
        if isinstance(x, dict):
            lines.append(f"- {x.get('id','?')}: {x.get('status','?')} - {x.get('title','')}")
        else:
            lines.append(f"- {x}")
    OUT1.parent.mkdir(parents=True,exist_ok=True)
    OUT1.write_text("\n".join(lines), encoding="utf-8")

    # Best-effort: sanitize any existing sessions/*/TASKS.md in place
    sess_root=ROOT/"sessions"
    if sess_root.exists():
        for p in sess_root.rglob("TASKS.md"):
            try:
                raw=p.read_text(encoding="utf-8",errors="ignore")
                p.write_text(to_ascii(raw), encoding="utf-8")
            except Exception: pass

if __name__=="__main__":
    write_ascii_tasks()
    print(str(OUT1))
