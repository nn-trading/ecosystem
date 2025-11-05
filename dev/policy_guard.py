from __future__ import annotations
import json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
POL=ROOT/"config/policy.yaml"
def _yload(p:Path):
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def check(action:str, level:str="medium")->dict:
    pol=_yload(POL)
    appr=(pol.get("approval",{}) or {}).get(level,"auto")
    allowed = (level!="high") or (appr=="auto")
    return {"action":action,"level":level,"approval":appr,"allowed":bool(allowed)}

if __name__=="__main__":
    print(json.dumps(check("plan_apply","medium"), ensure_ascii=True))
