import json, time
from pathlib import Path
p=Path('reports/chat/exact_tail.jsonl')
p.parent.mkdir(parents=True, exist_ok=True)
p.touch(exist_ok=True)
line={'ts': time.time(), 'role':'user', 'text':'count monitors only'}
with p.open('a', encoding='utf-8') as f:
    f.write(json.dumps(line, ensure_ascii=True)+'\n')
print('injected')
