import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
print('Brain chat ready. Type "exit" to quit.')
while True:
    try:
        line=input('You> ').strip()
    except EOFError:
        break
    if not line: continue
    if line.lower() in ('exit','quit'): break
    TAIL.parent.mkdir(parents=True, exist_ok=True)
    TAIL.open("a",encoding="utf-8").write(json.dumps({"ts":time.time(),"role":"user","text":line},ensure_ascii=False)+"\n")
