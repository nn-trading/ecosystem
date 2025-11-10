param([object]$KeepRunning = $true,[int]$WaitSec = 60)
# Normalize KeepRunning to boolean
if ($KeepRunning -is [string]) {
  $s = $KeepRunning.Trim().TrimStart('$').ToLower()
  if ($s -match '^(false|0)$') { $KeepRunning = $false }
  elseif ($s -match '^(true|1)$') { $KeepRunning = $true }
}
Set-StrictMode -Version 2; $ErrorActionPreference='Stop'
$ROOT='C:\bots\ecosys'; Set-Location -LiteralPath $ROOT
# Dirs + dual config
@('dev','config','configs','reports','reports\chat','reports\screens','logs','runs','logs\archive','reports\archive\chat')|%{New-Item -ItemType Directory -Force -Path $_|Out-Null}
Set-Content -Encoding Ascii -LiteralPath config\model.yaml  -Value 'default: gpt-5`nlock: true'
Set-Content -Encoding Ascii -LiteralPath configs\model.yaml -Value 'default: gpt-5`nlock: true'
Set-Content -Encoding Ascii -LiteralPath config\comms.yaml  -Value 'mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl'
Set-Content -Encoding Ascii -LiteralPath configs\comms.yaml -Value 'mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl'
if(!(Test-Path reports\chat\exact_tail.jsonl)){New-Item -ItemType File -Force -Path reports\chat\exact_tail.jsonl|Out-Null}
# Stop base background to clear tail lock
if(Test-Path .\start.ps1){powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null}
# Rotate logs/tail
$ts=Get-Date -Format 'yyyyMMdd_HHmmss'
foreach($p in @('logs\start_stdout.log','logs\start_stderr.log')){if(Test-Path $p){$t=('logs\archive\{0}_{1}.log' -f ([IO.Path]::GetFileNameWithoutExtension($p)),$ts);Move-Item $p $t -ErrorAction SilentlyContinue}}
if(Test-Path reports\chat\exact_tail.jsonl){ try { Move-Item reports\chat\exact_tail.jsonl ('reports\archive\chat\exact_tail_{0}.jsonl' -f $ts) -ErrorAction Stop } catch {} }
if(-not (Test-Path reports\chat\exact_tail.jsonl)){ New-Item -ItemType File -Force -Path reports\chat\exact_tail.jsonl|Out-Null }
# Venv + deps
$py=Join-Path $ROOT '.venv\Scripts\python.exe'
if(-not (Test-Path $py)){try{py -3 -m venv .venv}catch{python -m venv .venv}; $py=Join-Path $ROOT '.venv\Scripts\python.exe'}
& $py -m pip install -U pip | Out-Null
& $py -m pip install 'openai>=1,<2' fastapi uvicorn psutil requests pywin32 mss pillow screeninfo keyboard pyautogui | Out-Null
# Python modules
Set-Content -Encoding Ascii dev\auto_utils.py @'
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
'@
Set-Content -Encoding Ascii dev\tail_utils.py @'
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
'@
Set-Content -Encoding Ascii dev\tool_server.py @'
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
'@
Set-Content -Encoding Ascii dev\dispatcher.py @'
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
'@
Set-Content -Encoding Ascii dev\nl_router.py @'
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
'@
Set-Content -Encoding Ascii dev\tail_inject.py @'
import sys
from dev.tail_utils import append
txt=' '.join(sys.argv[1:]).strip() or 'count my monitors and save a short note'
append('user', txt)
print('injected')
'@
# kill old helpers
$pidsPath='reports\CORE01_FIX_PIDS.json'
if(Test-Path $pidsPath){try{$p=Get-Content $pidsPath|ConvertFrom-Json -ErrorAction SilentlyContinue; foreach($k in 'tool','dispatch','router'){ $pid=[int]$p.$k; if($pid -gt 0){Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue}}}catch{}}
$oldPids='reports\AUTONOMOUS_PIDS.json'
if(Test-Path $oldPids){try{$q=Get-Content $oldPids|ConvertFrom-Json -ErrorAction SilentlyContinue; foreach($k in 'tool','dispatch','router'){ $pid=[int]$q.$k; if($pid -gt 0){Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue}}}catch{}}
# launch helpers
$env:TOOL_SERVER_PORT='8766'
$tool=Start-Process -PassThru -WindowStyle Hidden $py -ArgumentList '-m','uvicorn','dev.tool_server:app','--host','127.0.0.1','--port',$env:TOOL_SERVER_PORT
# readiness
$deadline=(Get-Date).AddSeconds(15); $ready=$false
while((Get-Date) -lt $deadline){ try{ $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8766/ping' -TimeoutSec 2; if($r.Content -match 'ok'){ $ready=$true; break } }catch{}; Start-Sleep -Milliseconds 300 }
$disp=Start-Process -PassThru -WindowStyle Hidden $py -ArgumentList '-m','dev.dispatcher'
$rout=Start-Process -PassThru -WindowStyle Hidden $py -ArgumentList '-m','dev.nl_router'
@{tool=$tool.Id; dispatch=$disp.Id; router=$rout.Id} | ConvertTo-Json | Set-Content -Encoding Ascii $pidsPath
# events baseline
$shadow='reports\chat\exact_tail_shadow.jsonl'
$evPath='reports\DISPATCH_EVENTS.jsonl'; if(!(Test-Path $evPath)){New-Item -ItemType File -Force -Path $evPath|Out-Null}
$before=(Get-Content $evPath -ErrorAction SilentlyContinue).Length
# seed and wait
& $py -m dev.tail_inject 'count my monitors and save a short note'
$deadline=(Get-Date).AddSeconds($WaitSec); $ok=$false
while((Get-Date) -lt $deadline){
  if(Select-String -Path 'reports\chat\exact_tail.jsonl' -Pattern '\[ecosystem-result\]' -SimpleMatch){$ok=$true; break}
  if(Test-Path $shadow){ if(Select-String -Path $shadow -Pattern '\[ecosystem-result\]' -SimpleMatch){$ok=$true; break} }
  $after=(Get-Content $evPath -ErrorAction SilentlyContinue).Length
  if($after -gt $before){$ok=$true; break}
  Start-Sleep -Milliseconds 300
}
# summary
$sum=@('CORE01_FIX '+(Get-Date -Format s)); $sum+=('tool_server_pid='+$tool.Id); $sum+=('dispatcher_pid='+$disp.Id); $sum+=('router_pid='+$rout.Id); $sum+=('ok='+$ok)
Set-Content -Encoding Ascii reports\CORE01_FIX_SUMMARY.txt ($sum -join "`r`n")
if(-not $KeepRunning){foreach($p in @($tool.Id,$disp.Id,$rout.Id)){Stop-Process -Id $p -Force -ErrorAction SilentlyContinue}}
Write-Host ('=== CORE-01 FIXED === ok={0} keep_running={1}' -f $ok,$KeepRunning)
