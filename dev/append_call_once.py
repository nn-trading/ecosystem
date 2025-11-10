import json, time
from pathlib import Path
p=Path('reports/chat/exact_tail.jsonl')
p.parent.mkdir(parents=True, exist_ok=True)
p.touch(exist_ok=True)
obj={'ts': time.time(), 'role':'assistant', 'text':'[ecosystem-call] ' + json.dumps({'tool':'monitors','args':{}}, ensure_ascii=True)}
with p.open('a', encoding='utf-8') as f:
    f.write(json.dumps(obj, ensure_ascii=True)+'\n')
print('call-injected')
