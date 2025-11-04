from __future__ import annotations
import os, re, json, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CFG_AI = ROOT/"config/ai.yaml"
CFG_CORE= ROOT/"config/core.yaml"
REP    = ROOT/"reports"
PLANS  = REP/"plans"

def load_yaml(p:Path)->dict:
    try:
        import yaml
        return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
    except Exception:
        return {}

def llm_available()->bool:
    return bool(os.environ.get("OPENAI_API_KEY"))

def select_model()->str:
    cfg = load_yaml(CFG_AI).get("llm",{}) if CFG_AI.exists() else {}
    return os.environ.get(cfg.get("model_env","OPENAI_MODEL") or "") or cfg.get("default_model","gpt-4o-mini")

SYS_PROMPT = (
  "You are an intent-to-plan translator. Input is a user goal. "
  "Output minimal JSON with keys: {title, steps:[{action, params}], notes}. "
  "Actions allowed: create_agent, create_tool, touch_file, browser_probe. "
  "Never include secrets. Keep names short. Keep JSON ASCII-safe."
)

def plan_from_llm(text:str)->dict:
    from openai import OpenAI
    cfg = load_yaml(CFG_AI).get("llm",{}) if CFG_AI.exists() else {}
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = select_model()
    msg_user = f"Goal:\n{text}\n"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":SYS_PROMPT},{"role":"user","content":msg_user}],
        temperature=cfg.get("temperature",0.2),
        max_tokens=int(cfg.get("max_tokens",1200))
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        import json as _j
        return _j.loads(raw)
    except Exception:
        return {"title":"plan", "steps":[{"action":"touch_file","params":{"path":"reports\\intent_fallback.txt"}}], "notes":"fallback_parse"}

def plan_from_heuristic(text:str)->dict:
    t = text.lower()
    steps=[]
    if "agent" in t:
        steps.append({"action":"create_agent","params":{"name":"Echo Worker","deps":["httpx"]}})
    elif "tool" in t:
        steps.append({"action":"create_tool","params":{"name":"Hello Tool","pip":["httpx"]}})
    else:
        steps.append({"action":"touch_file","params":{"path":"reports\\intent_note.txt"}})
    return {"title":"plan","steps":steps,"notes":"heuristic"}

def write_plan(obj:dict)->Path:
    PLANS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = PLANS/f"plan_{ts}.json"
    # Enforce ASCII-only to avoid non-ASCII artifacts
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=True), encoding="utf-8")
    return p

def handle_text(text:str)->Path:
    if llm_available():
        obj = plan_from_llm(text)
    else:
        obj = plan_from_heuristic(text)
    return write_plan(obj)

def sweep_inbox()->int:
    cfg = load_yaml(CFG_CORE).get("core01",{}) if CFG_CORE.exists() else {}
    inbox = ROOT/(cfg.get("intents_inbox") or "reports\\intents_in.jsonl")
    offp  = REP/"intents_offset.txt"
    inbox.parent.mkdir(parents=True, exist_ok=True); inbox.touch(exist_ok=True)
    pos = int(offp.read_text(encoding="utf-8").strip()) if offp.exists() else 0
    data = inbox.read_bytes()
    new = data[pos:].decode("utf-8","ignore").splitlines()
    count = 0
    for line in new:
        line=line.strip()
        if not line: continue
        try:
            obj=json.loads(line)
            text=(obj.get("text") or "").strip()
            if text:
                handle_text(text); count+=1
        except Exception:
            pass
    offp.write_text(str(len(data)), encoding="utf-8")
    return count

def main():
    import sys
    if len(sys.argv)>=2 and sys.argv[1]=="loop":
        while True:
            try: sweep_inbox()
            except Exception: pass
            time.sleep(3)
    elif len(sys.argv)>=3 and sys.argv[1]=="one":
        text=" ".join(sys.argv[2:])
        p=handle_text(text); print(str(p))
    else:
        print("Usage: python dev\\core01_intent.py loop | one <text>")

if __name__=="__main__": main()
