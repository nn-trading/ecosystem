# dev/config_guard.py
from __future__ import annotations
import os, json, tempfile, shutil
from pathlib import Path
try:
    import yaml  # optional
    def yload(p:Path):
        return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
except Exception:
    def yload(p:Path):
        return {}

ROOT=Path(__file__).resolve().parents[1]

def atomic_write(path:Path, text:str):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write(text)
        tmp=Path(f.name)
    shutil.move(str(tmp), str(path))

def load_cfg(name:str, defaults:dict)->tuple[dict,list]:
    p=ROOT/("config/"+name)
    cfg = {}
    try: cfg=yload(p) or {}
    except Exception: cfg={}
    # env overrides like FOO_BAR -> foo.bar (simple underscore to dot map)
    over={}
    for k,v in os.environ.items():
        if k.startswith("ECOSYS_"):
            key=k[len("ECOSYS_"):].lower().replace("__",".").replace("_",".")
            over[key]=v
    # apply overrides (flat keys)
    for k,v in over.items():
        cfg[k]=v
    # fill defaults
    for k,v in defaults.items():
        cfg.setdefault(k,v)
    problems=[]
    return cfg, problems

if __name__=="__main__":
    cfg, problems = load_cfg("db.yaml", {"default_memory_db":"var/events.db"})
    info={"ok": True, "problems": problems, "sample": cfg}
    print(json.dumps(info, ensure_ascii=True))
