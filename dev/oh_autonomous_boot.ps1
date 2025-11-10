param(
  [switch]$KeepRunning,
  [switch]$LaunchChat,
  [int]$BasePort=8765
)
$ErrorActionPreference='Stop'

#  paths & dirs
$ROOT=(Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).Parent.FullName
$DEV =Join-Path $ROOT 'dev'
$CFG =Join-Path $ROOT 'config'
$CFG2=Join-Path $ROOT 'configs'
$RPT =Join-Path $ROOT 'reports'
$CHAT=Join-Path $RPT  'chat'
$RT  =Join-Path $CHAT 'exact_tail.jsonl'
$RTS =Join-Path $CHAT 'exact_tail_shadow.jsonl'
$SCR =Join-Path $RPT  'screens'
$LOG =Join-Path $ROOT 'logs'
$LAR =Join-Path $LOG  'archive'
$RAR =Join-Path $ROOT 'reports\archive\chat'
$RUN =Join-Path $ROOT 'runs'
$PIDF=Join-Path $RPT  'AUTONOMOUS_PIDS.json'

New-Item -ItemType Directory -Force -Path $DEV,$CFG,$CFG2,$RPT,$CHAT,$SCR,$LOG,$LAR,$RAR,$RUN | Out-Null
if (!(Test-Path (Join-Path $DEV '__init__.py'))) { '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '__init__.py') }

#  dual config (handles config\ or configs\)
$mdl="default: gpt-5`nlock: true"
$cms="mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl"
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG  'model.yaml') -Value $mdl
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG2 'model.yaml') -Value $mdl
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG  'comms.yaml') -Value $cms
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG2 'comms.yaml') -Value $cms
if (!(Test-Path $RT))  { '' | Set-Content -Encoding Ascii -LiteralPath $RT }
if (!(Test-Path $RTS)) { '' | Set-Content -Encoding Ascii -LiteralPath $RTS }

#  python modules: autoname utils
$auto_utils=@'
from pathlib import Path
import time
def unique_path(dirpath, stem, ext, limit=999):
    d=Path(dirpath); d.mkdir(parents=True, exist_ok=True)
    p=d/f"{stem}{ext}"
    if not p.exists(): return str(p)
    for i in range(1,limit+1):
        q=d/f"{stem}_{i:03d}{ext}"
        if not q.exists(): return str(q)
    return str(d/f"{stem}_{int(time.time())}{ext}")
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'auto_utils.py') -Value $auto_utils

#  python modules: local tools (PC control)
$local_tools=@'
import os, json, time, subprocess
from pathlib import Path
from .auto_utils import unique_path
ROOT = Path(__file__).resolve().parents[1]
DESK = Path(os.path.expanduser("~")) / "Desktop"
RPTS = ROOT / "reports"; (RPTS / "screens").mkdir(parents=True, exist_ok=True)

def count_monitors():
    try:
        from screeninfo import get_monitors
        return {"monitors": len(get_monitors())}
    except Exception as e:
        return {"monitors": 0, "error": str(e)}

def count_windows():
    try:
        import win32gui
        def visible(h): return win32gui.IsWindowVisible(h) and bool(win32gui.GetWindowText(h))
        wins=[]
        def enum(h,_): 
            if visible(h): wins.append(h)
        win32gui.EnumWindows(enum, None)
        return {"windows": len(wins)}
    except Exception as e:
        return {"windows": 0, "error": str(e)}

def screenshot_autoname(stem="shot"):
    from mss import mss
    p = (RPTS/"screens"/f"{stem}_{time.strftime('%Y%m%d_%H%M%S')}.png")
    with mss() as s: s.shot(output=str(p))
    return {"path": str(p)}

def write_text_autoname(stem="note", text="OK"):
    p = Path(unique_path(DESK, stem, ".txt"))
    p.write_text(text, encoding="utf-8")
    return {"path": str(p)}

def open_notepad(path):
    try:
        subprocess.Popen(["notepad.exe", str(path)])
        return {"opened": True, "path": str(path)}
    except Exception as e:
        return {"opened": False, "error": str(e)}
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'local_tools.py') -Value $local_tools

#  tool server (FastAPI)
$tool_server=@'
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from .local_tools import count_monitors, count_windows, screenshot_autoname, write_text_autoname, open_notepad

app = FastAPI(title="Ecosys Tool Server")

class WriteReq(BaseModel):
    stem: str = "note"
    text: Optional[str] = "OK"

class ShotReq(BaseModel):
    stem: str = "shot"

class NotepadReq(BaseModel):
    path: str

@app.get("/monitors")
def monitors():
    return count_monitors()

@app.get("/windows")
def windows():
    return count_windows()

@app.post("/screenshot")
def screenshot(req: ShotReq):
    return screenshot_autoname(req.stem)

@app.post("/write")
def write(req: WriteReq):
    return write_text_autoname(req.stem, req.text or "")

@app.post("/notepad")
def notepad(req: NotepadReq):
    return open_notepad(req.path)
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'tool_server.py') -Value $tool_server

#  dispatcher (executes structured calls, tail+shadow writeback)
$dispatcher=@'
import json, time, http.client, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
SHDW = ROOT / "reports" / "chat" / "exact_tail_shadow.jsonl"
EVT  = ROOT / "reports" / "DISPATCH_EVENTS.jsonl"

def http_post(host, port, path, payload):
    conn = http.client.HTTPConnection(host, port, timeout=8)
    body = json.dumps(payload)
    conn.request("POST", path, body=body, headers={"Content-Type":"application/json"})
    resp = conn.getresponse(); data = resp.read()
    try: return json.loads(data.decode("utf-8","ignore"))
    except: return {"status": resp.status, "raw": data.decode("utf-8","ignore")}

def http_get(host, port, path):
    conn = http.client.HTTPConnection(host, port, timeout=8)
    conn.request("GET", path); resp = conn.getresponse(); data = resp.read()
    try: return json.loads(data.decode("utf-8","ignore"))
    except: return {"status": resp.status, "raw": data.decode("utf-8","ignore")}

def append_tail(obj):
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    try:
        with TAIL.open("a", encoding="utf-8") as f: f.write(line); return True
    except Exception:
        try:
            with SHDW.open("a", encoding="utf-8") as f: f.write(line); return True
        except Exception:
            return False

def dispatch(call, host, port):
    tool = call.get("tool"); args = call.get("args") or {}
    if tool == "monitors":   return http_get(host, port, "/monitors")
    if tool == "windows":    return http_get(host, port, "/windows")
    if tool == "screenshot": return http_post(host, port, "/screenshot", {"stem": args.get("stem","shot")})
    if tool == "write":      return http_post(host, port, "/write", {"stem": args.get("stem","note"), "text": args.get("text","OK")})
    if tool == "notepad":    return http_post(host, port, "/notepad", {"path": args.get("path","")})
    return {"error": f"unknown tool '{tool}'"}

def loop(host, port):
    seen = 0
    while True:
        try:
            lines=[]
            if TAIL.exists():
                raw = TAIL.read_text(encoding='utf-8', errors='ignore').splitlines()
                if len(raw)>seen: lines=raw[seen:]; seen=len(raw)
            for ln in lines:
                try:
                    obj=json.loads(ln)
                    txt=str(obj.get('text',''))
                    if txt.startswith('[ecosystem-call]'):
                        payload=json.loads(txt.split(']',1)[1].strip())
                        res=dispatch(payload, host, port)
                        EVT.parent.mkdir(parents=True, exist_ok=True)
                        EVT.open('a',encoding='utf-8').write(json.dumps({'call':payload,'result':res})+'\n')
                        append_tail({'ts':time.time(),'role':'assistant','text':f'[ecosystem-result] {res}'})
                except Exception:
                    pass
            time.sleep(1)
        except Exception:
            time.sleep(2)

if __name__=='__main__':
    host=os.environ.get('ECOSYS_TOOL_HOST','127.0.0.1')
    port=int(os.environ.get('ECOSYS_TOOL_PORT','8765'))
    loop(host, port)
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'dispatcher.py') -Value $dispatcher

#  NL router (autonomous: turns natural language into structured calls using GPT-5 with offline fallback)
$router=@'
import os, json, time, re
from pathlib import Path
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
OUT  = ROOT / "reports" / "ROUTER_EVENTS.jsonl"

def read_api_key():
    k=os.environ.get("OPENAI_API_KEY")
    if k: return k
    p=ROOT / "api_key.txt"
    if p.exists():
        try: return p.read_text(encoding="utf-8", errors="ignore").strip()
        except: pass
    return None

_SIMPLE_PATS = [
    (re.compile(r"monitors|screens?\\b", re.I), {"tool":"monitors","args":{}}),
    (re.compile(r"windows?\\b", re.I), {"tool":"windows","args":{}}),
    (re.compile(r"screenshot|screen shot|capture\\b", re.I), {"tool":"screenshot","args":{"stem":"auto"}}),
    (re.compile(r"write|note|saying\\b", re.I), {"tool":"write","args":{"stem":"note","text":"ALL GREEN"}}),
]

def _simple_map(ut:str):
    for rx, call in _SIMPLE_PATS:
        if rx.search(ut):
            return json.loads(json.dumps(call))
    return {"tool":"write","args":{"stem":"router_note","text":ut[:200]}}

def to_call(user_text:str):
    ut=(user_text or '').strip()
    key=read_api_key()
    if not key or OpenAI is None:
        return _simple_map(ut)
    try:
        sys = (
          "You translate user text into a single JSON tool call.\n"
          "Allowed tools: monitors, windows, screenshot, write, notepad.\n"
          "Schema: {\"tool\": <name>, \"args\": { ... }}. "
          "For screenshot, default stem='shot'. For write, include a short 'text' if sensible; stem default 'note'. "
          "For notepad, include a 'path' only if the user mentions an existing file; otherwise prefer write.\n"
          "Return ONLY JSON. No extra text."
        )
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role":"system","content":sys},{"role":"user","content":ut}],
            temperature=0,
            max_completion_tokens=128
        )
        raw=r.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception:
        return _simple_map(ut)

def append_tail(obj):
    try:
        with TAIL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False)+"\n")
        return True
    except Exception:
        return False

def follow():
    seen = 0
    while True:
        try:
            lines=[]
            if TAIL.exists():
                raw=TAIL.read_text(encoding="utf-8", errors="ignore").splitlines()
                if len(raw)>seen: lines=raw[seen:]; seen=len(raw)
            for ln in lines:
                try:
                    obj=json.loads(ln)
                    if obj.get("role")=="user":
                        call=to_call(str(obj.get("text","")))
                        OUT.parent.mkdir(parents=True, exist_ok=True)
                        OUT.open("a",encoding="utf-8").write(json.dumps({"user":obj.get("text",""),"call":call})+"\n")
                        append_tail({"ts":time.time(),"role":"assistant","text":"[ecosystem-call] "+json.dumps(call,ensure_ascii=False)})
                except Exception:
                    pass
            time.sleep(1)
        except Exception:
            time.sleep(2)

if __name__=='__main__':
    follow()
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'nl_router.py') -Value $router

#  optional chat (robust, no planner noise)
$chat_py=@'
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
print('Brain chat ready. Type "exit" to quit.')
while True:
    try:
        line=input('You> ').strip()
    except EOFError:
        break
    if not line: continue
    if line.lower() in ('exit','quit'): break
    TAIL.parent.mkdir(parents=True, exist_ok=True)
    TAIL.open("a",encoding="utf-8").write(json.dumps({"ts":time.time(),"role":"user","text":line},ensure_ascii=False)+"\n")
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'brain_chat_shell.py') -Value $chat_py

#  venv + deps
$py=Join-Path $ROOT '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $ROOT '.venv') } else { python -m venv (Join-Path $ROOT '.venv') }
  $py=Join-Path $ROOT '.venv\Scripts\python.exe'
}
& $py -m pip -q install -U pip | Out-Null
& $py -m pip -q install fastapi uvicorn 'openai>=1,<2' mss pillow screeninfo pywin32 psutil requests | Out-Null

#  rotate logs & tail
$ts=Get-Date -Format 'yyyyMMdd_HHmmss'
$std=Join-Path $LOG 'start_stdout.log'
$err=Join-Path $LOG 'start_stderr.log'
try{ powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null }catch{}
if(Test-Path $std){ Move-Item -Force $std (Join-Path $LAR ('start_stdout_'+$ts+'.log')) }
if(Test-Path $err){ Move-Item -Force $err (Join-Path $LAR ('start_stderr_'+$ts+'.log')) }
if(Test-Path $RT ){ Move-Item -Force $RT  (Join-Path $RAR ('exact_tail_'+$ts+'.jsonl')) }
'' | Set-Content -Encoding Ascii -LiteralPath $RT
'' | Set-Content -Encoding Ascii -LiteralPath $RTS

#  start headless background (ecosystem base)
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
Start-Sleep -Seconds 2

#  choose free port for tool server
$port=$BasePort
for($i=0;$i -lt 10;$i++){
  try {
    $tcp = New-Object System.Net.Sockets.TcpListener([Net.IPAddress]::Loopback,$port)
    $tcp.Start(); $tcp.Stop(); break
  } catch { $port++ }
}

#  launch tool server, dispatcher, NL router
$env:ECOSYS_TOOL_HOST='127.0.0.1'
$env:ECOSYS_TOOL_PORT="$port"
$toolArgs = @('-m','uvicorn','dev.tool_server:app','--host',$env:ECOSYS_TOOL_HOST,'--port',"$port",'--log-level','warning')
$toolProc = Start-Process -PassThru -FilePath $py -ArgumentList $toolArgs -WorkingDirectory $ROOT
$dispProc = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','dev.dispatcher') -WorkingDirectory $ROOT
$routerProc = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','dev.nl_router') -WorkingDirectory $ROOT

#  persist PIDs
$pidObj=@{ tool=$toolProc.Id; dispatch=$dispProc.Id; router=$routerProc.Id; port=$port }
($pidObj | ConvertTo-Json) | Set-Content -Encoding Ascii -LiteralPath $PIDF

#  optionally launch chat (off by default)
if ($LaunchChat) {
  Start-Process -FilePath $py -ArgumentList @('-m','dev.brain_chat_shell') -WorkingDirectory $ROOT | Out-Null
}

#  quick health/verification (seed + probe)
$seed='{"ts":'+[string](Get-Date -Date (Get-Date) -UFormat %s)+' ,"role":"assistant","text":"[ecosystem-call] {\"tool\":\"write\",\"args\":{\"stem\":\"auto_probe\",\"text\":\"AUTONOMOUS OK\"}}"}'
Add-Content -Encoding Ascii -LiteralPath $RT -Value $seed
Start-Sleep -Seconds 3
$probe = (Get-Content (Join-Path $ROOT 'reports\DISPATCH_EVENTS.jsonl') -ErrorAction SilentlyContinue | Select-Object -Last 3) -join [Environment]::NewLine

#  bundle
$bundle = Join-Path $RUN ('autonomous_boot_'+$ts)
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
$files=@(
  $RT, (Join-Path $CHAT 'exact_tail_shadow.jsonl'),
  (Join-Path $RPT 'DISPATCH_EVENTS.jsonl'),
  (Join-Path $RPT 'ROUTER_EVENTS.jsonl'),
  (Join-Path $RPT 'AUTONOMOUS_PIDS.json')
)
foreach($p in $files){ if(Test-Path $p){ Copy-Item -Force $p $bundle } }
Compress-Archive -Force -Path (Join-Path $bundle '*') -DestinationPath ($bundle+'.zip')

Write-Host '=== AUTONOMOUS STACK ONLINE ==='
Write-Host ('Tool server port: ' + $port)
Write-Host ('Bundle: ' + ($bundle+'.zip'))
Write-Host 'Background kept running.'
if(-not $KeepRunning){
  & (Join-Path $DEV 'oh_autonomous_stop.ps1')
}
