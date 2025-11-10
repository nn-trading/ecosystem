import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
SHDW = ROOT / "reports" / "chat" / "exact_tail_shadow.jsonl"
EVT  = ROOT / "reports" / "DISPATCH_EVENTS.jsonl"

def has_ok(p):
    if not p.exists(): return False
    for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines()[-400:]:
        try:
            obj=json.loads(ln)
            if obj.get("role")=="assistant" and str(obj.get("text","")).startswith("[ecosystem-result]"):
                return True
        except: pass
    return False

ok = has_ok(TAIL) or has_ok(SHDW)
if not ok and EVT.exists():
    for ln in EVT.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]:
        try:
            obj=json.loads(ln)
            if obj.get("call") and obj.get("result"): ok=True; break
        except: pass

print("OK" if ok else "NO")
