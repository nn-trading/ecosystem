import os, json, time
from dev.tail_utils import append, TAIL
from dev.auto_utils import read_api_key
from openai import OpenAI
MODEL='gpt-5'; client=OpenAI(api_key=read_api_key())
SYS=('You are a router. Output ONLY JSON like {\"tool\":\"write|screenshot|monitors|windows\",\"args\":{...}}. '
     'If user asks to save or note -> write(text=...), if screenshot -> screenshot, if monitors/windows -> respective.')
def tail_iter(p):
    with open(p,'r',encoding='utf-8',errors='ignore') as f:
        f.seek(0,2)
        while True:
            line=f.readline()
            if not line: time.sleep(0.2); continue
            yield line
def decide(txt):
    try:
        r=client.chat.completions.create(model=MODEL, messages=[{'role':'system','content':SYS},{'role':'user','content':txt[:400]}], temperature=0, max_completion_tokens=128)
        c=(r.choices[0].message.content or '').strip()
        return json.loads(c)
    except Exception:
        return {'tool':'write','args':{'text':('Note: '+txt[:200])}}
def main():
    for raw in tail_iter(TAIL):
        try: obj=json.loads(raw)
        except: continue
        if obj.get('role')=='user':
            call=decide((obj.get('text') or '').strip())
            append('assistant','[ecosystem-call] '+json.dumps(call,ensure_ascii=True))
if __name__=='__main__': main()
