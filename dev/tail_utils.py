import os, json
from datetime import datetime
def _root(): return os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
TAIL=os.path.join(_root(),'reports','chat','exact_tail.jsonl')
SHADOW=os.path.join(_root(),'reports','chat','exact_tail_shadow.jsonl')
def now(): return datetime.utcnow().isoformat()
def append(role,text):
    line={"ts":now(),"role":role,"text":str(text)}
    try:
        os.makedirs(os.path.dirname(TAIL),exist_ok=True)
        with open(TAIL,'a',encoding='utf-8',errors='ignore') as f: f.write(json.dumps(line,ensure_ascii=True)+'\n')
    except Exception:
        with open(SHADOW,'a',encoding='utf-8',errors='ignore') as f: f.write(json.dumps(line,ensure_ascii=True)+'\n')
