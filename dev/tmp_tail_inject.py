import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / 'reports' / 'chat' / 'exact_tail.jsonl'
TAIL.parent.mkdir(parents=True, exist_ok=True)
TAIL.open('a', encoding='utf-8').write(json.dumps({'ts': time.time(), 'role':'user', 'text':'count my monitors'}, ensure_ascii=False)+'\n')
print('injected user line into', TAIL)
