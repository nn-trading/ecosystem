from __future__ import annotations
import json, time, re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CFG  = ROOT/"config/core.yaml"
SKL  = ROOT/"config/skills.yaml"
REP  = ROOT/"reports"

def load_yaml(p:Path)->dict:
    try:
        import yaml
        return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
    except Exception:
        return {}

def slug(s:str)->str:
    s=re.sub(r"[^A-Za-z0-9]+","-",s.strip().lower())
    return re.sub(r"-+","-",s).strip("-") or "name"

def write_text(p:Path, text:str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def build_agent_spec(name:str, deps:list[str], skills:dict)->str:
    allow = set((skills.get("create_agent") or {}).get("deps_allow") or [])
    deps2 = [d for d in (deps or []) if d in allow]
    return "name: \""+name+"\"\n" + ("deps: [" + ", ".join("\""+d+"\"" for d in deps2) + "]\n")

def build_tool_spec(name:str, pip:list[str], skills:dict)->str:
    allow = set((skills.get("create_tool") or {}).get("deps_allow") or [])
    pkgs = [p for p in (pip or []) if p in allow]
    return "name: \""+name+"\"\n" + ("pip: [" + ", ".join("\""+p+"\"" for p in pkgs) + "]\n") + \
           "files:\n  - use_template: \"py_module\"\n    path: \"tools\\generated\\module.py\"\n    module_name: \"tools.generated.module\"\n"

def apply_plan(plan_path:Path)->dict:
    cfg = load_yaml(CFG)
    skl = (load_yaml(SKL) or {}).get("skills",{})
    core2 = cfg.get("core02",{}) if cfg else {}
    inbox_agents = ROOT/(core2.get("inbox_agents") or "reports\\inbox")
    inbox_tools  = ROOT/(core2.get("inbox_tools") or "reports\\inbox_tools")
    actions_dir  = ROOT/(core2.get("actions_dir") or "reports\\actions")
    actions = []
    obj=json.loads(plan_path.read_text(encoding="utf-8"))
    for i, st in enumerate(obj.get("steps") or []):
        act=(st.get("action") or "").strip()
        par=st.get("params") or {}
        if act=="create_agent":
            name = par.get("name") or ("Agent "+slug(obj.get("title") or "agent"))
            spec = build_agent_spec(name, par.get("deps") or [], skl)
            out = ROOT/"specs/generated"/f"{slug(name)}_agent.yaml"
            write_text(out, spec)
            write_text(inbox_agents/out.name, spec)
            actions.append({"i":i,"action":"create_agent","spec":str(out)})
        elif act=="create_tool":
            name = par.get("name") or ("Tool "+slug(obj.get("title") or "tool"))
            spec = build_tool_spec(name, par.get("pip") or [], skl)
            out = ROOT/"specs/generated"/f"{slug(name)}_tool.yaml"
            write_text(out, spec)
            write_text(inbox_tools/out.name, spec)
            actions.append({"i":i,"action":"create_tool","spec":str(out)})
        elif act=="touch_file":
            pth = par.get("path") or "reports\\touch.txt"
            write_text(ROOT/pth, "touched "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
            actions.append({"i":i,"action":"touch_file","path":pth})
        elif act=="browser_probe":
            intent = {"url": par.get("url") or None, "ts": datetime.now().isoformat()}
            write_text(actions_dir/f"browser_intent_{i}.json", json.dumps(intent))
            actions.append({"i":i,"action":"browser_probe","intent":"written"})
    result = {"ok": True, "plan": str(plan_path), "actions": actions}
    write_text(REP/"last_apply.json", json.dumps(result, indent=2))
    return result

def latest_plan()->Path|None:
    ps=sorted((ROOT/"reports/plans").glob("plan_*.json"))
    return ps[-1] if ps else None

def loop():
    seen=set()
    (ROOT/"reports/plans").mkdir(parents=True, exist_ok=True)
    while True:
        for p in sorted((ROOT/"reports/plans").glob("plan_*.json")):
            if p.name in seen: continue
            try: apply_plan(p); seen.add(p.name)
            except Exception: pass
        time.sleep(3)

def main():
    import sys, json as _j
    if len(sys.argv)>=2 and sys.argv[1]=="loop":
        loop()
    elif len(sys.argv)>=2 and sys.argv[1]=="apply":
        p = latest_plan()
        if not p: print('{"ok":false,"error":"no plan"}'); return
        print(_j.dumps(apply_plan(p), indent=2))
    else:
        print("Usage: python dev\\core02_planner.py loop | apply")

if __name__=="__main__": main()
