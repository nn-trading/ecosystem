import os, json, time, requests
from dev.tail_utils import append, TAIL
from dev.auto_utils import root_dir
PORT=int(os.getenv('TOOL_SERVER_PORT','8766')); TOOL=f'http://127.0.0.1:{PORT}'
def handle_call(call):
    tool=call.get('tool'); args=call.get('args') or {}
    try:
        if tool=='write':      return requests.post(f'{TOOL}/write',json={'text':args.get('text',''),'stem':args.get('stem')}).json()
        if tool=='screenshot': return requests.post(f'{TOOL}/screenshot').json()
        if tool=='monitors':   return requests.get(f'{TOOL}/monitors').json()
        if tool=='windows':    return requests.get(f'{TOOL}/windows').json()
        return {'ok':False,'error':'unknown_tool'}
    except Exception as e: return {'ok':False,'error':str(e)}
def tail_iter(p):
    with open(p,'r',encoding='utf-8',errors='ignore') as f:
        f.seek(0,2)
        while True:
            line=f.readline()
            if not line: time.sleep(0.2); continue
            yield line
def main():
    ev=os.path.join(root_dir(),'reports','DISPATCH_EVENTS.jsonl'); os.makedirs(os.path.dirname(ev),exist_ok=True)
    for raw in tail_iter(TAIL):
        try: obj=json.loads(raw)
        except: continue
        text=str(obj.get('text') or '').strip()
        if obj.get('role')=='assistant' and text.startswith('[ecosystem-call]'):
            try: call=json.loads(text.split('] ',1)[1])
            except: continue
            res=handle_call(call)
            append('assistant','[ecosystem-result] '+json.dumps(res,ensure_ascii=True))
            with open(ev,'a',encoding='utf-8',errors='ignore') as ef: ef.write(json.dumps({'call':call,'result':res})+'\n')
if __name__=='__main__': main()
