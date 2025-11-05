# dev/chatops_cli.py (ASCII-only)
import sys, json, time, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
IN = ROOT/"reports/intents_in.jsonl"
OUT = ROOT/"specs/generated"

_HDR = [
    "SPEC SEED",
    "format: ascii",
    "version: 1"
]

def _slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s[:48] or "ask"

def submit(text: str):
    IN.parent.mkdir(parents=True, exist_ok=True)
    with IN.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"text": text}, ensure_ascii=True)+"\n")

def seed_spec(ask: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    name = f"ask_{ts}_{_slug(ask)}.txt"
    p = OUT/name
    lines = list(_HDR)
    lines += ["created: "+ts, "ask: "+ask, "status: seeded"]
    p.write_text("\n".join(lines)+"\n", encoding="ascii", errors="ignore")
    return str(p)

def main():
    if len(sys.argv) < 2:
        print('Usage: python dev\\chatops_cli.py "your goal sentence"'); return
    ask = " ".join(sys.argv[1:])
    submit(ask)
    spec_path = seed_spec(ask)
    print(json.dumps({"ok": True, "spec": spec_path}, ensure_ascii=True))

if __name__=="__main__":
    main()
