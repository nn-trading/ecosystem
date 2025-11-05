from __future__ import annotations
import os, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config/model_router.yaml"

def _yload(p:Path):
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def choose(task:str)->str:
    cfg=_yload(CFG)
    for r in cfg.get("routing_rules",[]):
        if f"task == '{task}'"==r.get("when"):
            return os.environ.get("OPENAI_MODEL") or r.get("use") or cfg.get("default","gpt-4o-mini")
    return os.environ.get("OPENAI_MODEL") or cfg.get("default","gpt-4o-mini")

if __name__=="__main__":
    print(json.dumps({"plan":choose("plan"),"summarize":choose("summarize")}, ensure_ascii=True))
