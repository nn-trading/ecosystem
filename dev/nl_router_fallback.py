import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL   = ROOT / "reports/chat/exact_tail.jsonl"
SHADOW = ROOT / "reports/chat/exact_tail_shadow.jsonl"
ROUTE  = ROOT / "reports/ROUTER_EVENTS.jsonl"

def append_tail(obj):
    try:
        TAIL.parent.mkdir(parents=True, exist_ok=True)
        with TAIL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=True)+"\n")
    except Exception:
        SHADOW.parent.mkdir(parents=True, exist_ok=True)
        with SHADOW.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=True)+"\n")

def log_route(obj):
    ROUTE.parent.mkdir(parents=True, exist_ok=True)
    with ROUTE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True)+"\n")

def to_call(text):
    t=(text or '').lower()
    if 'screenshot' in t:
        return {'tool':'screenshot','args':{}}
    if 'monitor' in t or 'screen' in t:
        return {'tool':'monitors','args':{}}
    if 'window' in t:
        return {'tool':'windows','args':{}}
    return {'tool':'write','args':{'text': (text or '')[:500]}}

def main():
    TAIL.parent.mkdir(parents=True, exist_ok=True)
    TAIL.touch(exist_ok=True)
    pos=0
    while True:
        try:
            with TAIL.open('r', encoding='utf-8') as f:
                f.seek(pos)
                for line in f:
                    pos=f.tell()
                    try:
                        obj=json.loads(line)
                    except Exception:
                        continue
                    if obj.get('role')=='user' and obj.get('text'):
                        call=to_call(obj['text'])
                        append_tail({'ts': time.time(), 'role':'assistant', 'text': '[ecosystem-call] '+json.dumps(call, ensure_ascii=True)})
                        log_route({'ts': time.time(), 'route':'fallback', 'text': obj['text'], 'call': call})
        except Exception:
            time.sleep(0.5)
        time.sleep(0.5)

if __name__=='__main__':
    main()
