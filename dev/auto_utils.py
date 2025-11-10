import os, json
def unique_path(path):
    base,ext=os.path.splitext(path); c=0; cand=path
    while os.path.exists(cand):
        c+=1; cand=f"{base}_{c:03d}{ext}"
    return cand
def root_dir(): return os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
def desktop_dir(): return os.path.join(os.path.expanduser('~'),'Desktop')
def read_api_key():
    p=os.path.join(root_dir(),'api_key.txt')
    if os.path.isfile(p):
        try: return open(p,'r',encoding='utf-8',errors='ignore').read().strip()
        except: pass
    return os.getenv('OPENAI_API_KEY')
def jsonl_append(path,obj):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,'a',encoding='utf-8',errors='ignore') as f: f.write(json.dumps(obj,ensure_ascii=True)+'\n')
