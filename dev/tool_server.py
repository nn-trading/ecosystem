from fastapi import FastAPI
from pydantic import BaseModel
import os, ctypes, time, mss, mss.tools
from screeninfo import get_monitors
from dev.auto_utils import unique_path, root_dir, desktop_dir
app=FastAPI(); ROOT=root_dir()
class WriteReq(BaseModel): text:str; stem:str|None=None
@app.get('/ping')     def ping():      return {'ok':True}
@app.get('/monitors') def monitors():  return {'monitors': len(get_monitors())}
def _count_windows():
    u=ctypes.windll.user32; titles=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(h,l):
        if u.IsWindowVisible(h):
            n=u.GetWindowTextLengthW(h)
            if n>0:
                b=ctypes.create_unicode_buffer(n+1); u.GetWindowTextW(h,b,n+1)
                t=b.value.strip(); 
                if t: titles.append(t)
        return True
    u.EnumWindows(enum_proc,0)
    return len(titles)
@app.get('/windows')  def windows():   return {'windows': _count_windows()}
@app.post('/write')   def write(r:WriteReq):
    stem=r.stem or 'auto_note'; d=desktop_dir(); os.makedirs(d,exist_ok=True)
    path=unique_path(os.path.join(d,f'{stem}.txt'))
    with open(path,'w',encoding='utf-8',errors='ignore') as f: f.write(r.text)
    return {'ok':True,'path':path}
@app.post('/screenshot') def screenshot():
    out=os.path.join(ROOT,'reports','screens'); os.makedirs(out,exist_ok=True)
    base=os.path.join(out,f'screen_{int(time.time())}.png'); path=unique_path(base)
    with mss.mss() as s: shot=s.grab(s.monitors[0]); mss.tools.to_png(shot.rgb, shot.size, output=path)
    return {'ok':True,'path':path}
