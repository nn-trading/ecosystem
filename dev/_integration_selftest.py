import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
seed = {"ts": time.time(), "role":"assistant", "text": '[ecosystem-call] {"tool":"write","args":{"stem":"auto_probe","text":"AUTONOMOUS OK"}}'}
TAIL.open("a", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False)+"\n")
print("seeded")
