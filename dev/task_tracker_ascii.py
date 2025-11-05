# dev/task_tracker_ascii.py
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TASKS=ROOT/"logs/tasks.json"
OUT1=ROOT/"reports/TASKS_ASCII.md"

# Optional redaction to avoid leaking secrets in task notes/titles
try:
    from dev.redact import sanitize as redact_s
except Exception:
    def redact_s(s: str) -> str: return s

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
    # Build map of global task statuses by id to align session view
    gmap={}
    if isinstance(globs, dict):
        for k,v in globs.items():
            status=v.get("status") if isinstance(v,dict) else v
            title=v.get("title","") if isinstance(v,dict) else ""
            gmap[k] = {"status": status, "title": title}
            lines.append(f"- {k}: {status} - {title}")
    elif isinstance(globs, list):
        for x in globs:
            if isinstance(x, dict):
                k=x.get("id","?"); status=x.get("status","?"); title=x.get("title","")
                gmap[k] = {"status": status, "title": title}
                lines.append(f"- {k}: {status} - {title}")
            else:
                lines.append(f"- {x}")
    lines.append("")
    lines.append("## Session")
    for x in sess:
        if isinstance(x, dict):
            kid=x.get('id','?'); status=x.get('status','?'); title=x.get('title','') or ''
            if kid in gmap:
                status = gmap[kid].get('status', status) or status
                if not title:
                    title = gmap[kid].get('title','') or title
            lines.append(f"- {kid}: {status} - {title}")
        else:
            s=str(x)
            lines.append(f"- {s}")
    OUT1.parent.mkdir(parents=True,exist_ok=True)
    out_text = "\n".join(lines)
    out_text = to_ascii(redact_s(out_text))
    OUT1.write_text(out_text, encoding="utf-8")

    # Best-effort: sanitize any existing sessions/*/TASKS.md in place
    sess_root=ROOT/"sessions"
    if sess_root.exists():
        for p in sess_root.rglob("TASKS.md"):
            try:
                raw=p.read_text(encoding="utf-8",errors="ignore")
                p.write_text(to_ascii(redact_s(raw)), encoding="utf-8")
            except Exception: pass

if __name__=="__main__":
    write_ascii_tasks()
    print(str(OUT1))
