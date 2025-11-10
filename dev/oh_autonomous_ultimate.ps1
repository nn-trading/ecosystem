param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version 2

# ---------- paths ----------
$ROOT = (Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).Parent.FullName
$dev  = Join-Path $ROOT 'dev'
$CFG1 = Join-Path $ROOT 'config'
$CFG2 = Join-Path $ROOT 'configs'
$LOGS = Join-Path $ROOT 'logs'
$ARCH = Join-Path $LOGS 'archive'
$REP  = Join-Path $ROOT 'reports'
$CHAT = Join-Path $REP 'chat'
$TAIL = Join-Path $CHAT 'exact_tail.jsonl'
$SHDW = Join-Path $CHAT 'exact_tail_shadow.jsonl'
$RUNS = Join-Path $ROOT 'runs'
$OUT  = Join-Path $REP  'AUTONOMOUS_ULTIMATE_SUMMARY.txt'
$PIDS = Join-Path $REP  'AUTONOMOUS_PIDS.json'

# ---------- helpers ----------
function Ensure-Dir([string]$p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Write-Ascii([string]$p,[string]$txt){ $dir=Split-Path $p -Parent; if($dir){Ensure-Dir $dir}; Set-Content -Encoding Ascii -LiteralPath $p -Value $txt }
function Append-Ascii([string]$p,[string]$txt){ Add-Content -Encoding Ascii -LiteralPath $p -Value $txt }
function TS(){ (Get-Date -Format 'yyyyMMdd_HHmmss') }
function PythonExe(){
  $venv = Join-Path $ROOT '.venv\Scripts\python.exe'
  if(Test-Path $venv){ return $venv }
  $py = (Get-Command py -ErrorAction SilentlyContinue); if($py){ return 'py' }
  return 'python'
}
function PipInstall([string[]]$pkgs){
  $py = PythonExe
  & $py -m pip install --upgrade pip | Out-Null
  foreach($p in $pkgs){ & $py -m pip install $p | Out-Null }
}

# ---------- ensure structure ----------
Ensure-Dir $dev; Ensure-Dir $CFG1; Ensure-Dir $CFG2; Ensure-Dir $LOGS; Ensure-Dir $ARCH
Ensure-Dir $REP; Ensure-Dir $CHAT; Ensure-Dir (Join-Path $REP 'screens'); Ensure-Dir $RUNS
if(-not (Test-Path (Join-Path $dev '__init__.py'))){ Write-Ascii (Join-Path $dev '__init__.py') '' }

# ---------- dual config (ASCII, no emojis) ----------
$modelYaml = 'default: gpt-5
lock: true'
$commsYaml = 'mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl'
Write-Ascii (Join-Path $CFG1 'model.yaml') $modelYaml
Write-Ascii (Join-Path $CFG2 'model.yaml') $modelYaml
Write-Ascii (Join-Path $CFG1 'comms.yaml') $commsYaml
Write-Ascii (Join-Path $CFG2 'comms.yaml') $commsYaml

# ---------- rotate logs/tail safely ----------
$ts=TS
$stdout = Join-Path $LOGS 'start_stdout.log'
$stderr = Join-Path $LOGS 'start_stderr.log'
try { if(Test-Path $stdout){ Move-Item -Force $stdout (Join-Path $ARCH ('start_stdout_{0}.log' -f $ts)) } } catch { Copy-Item $stdout (Join-Path $ARCH ('start_stdout_{0}.log' -f $ts)) -ErrorAction SilentlyContinue }
try { if(Test-Path $stderr){ Move-Item -Force $stderr (Join-Path $ARCH ('start_stderr_{0}.log' -f $ts)) } } catch { Copy-Item $stderr (Join-Path $ARCH ('start_stderr_{0}.log' -f $ts)) -ErrorAction SilentlyContinue }
try { if(Test-Path $TAIL){ Ensure-Dir (Join-Path $REP 'archive\chat'); Move-Item -Force $TAIL (Join-Path $REP ('archive\chat\exact_tail_{0}.jsonl' -f $ts)) } } catch { Copy-Item $TAIL (Join-Path $REP ('archive\chat\exact_tail_{0}.jsonl' -f $ts)) -ErrorAction SilentlyContinue }
if(-not (Test-Path $TAIL)){ Write-Ascii $TAIL '' }

# ---------- venv + deps ----------
$py = PythonExe
if(-not (Test-Path (Join-Path $ROOT '.venv'))){
  if($py -eq 'py'){ & $py -3 -m venv (Join-Path $ROOT '.venv') } else { & $py -m venv (Join-Path $ROOT '.venv') }
}
$py = PythonExe
PipInstall @('openai>=1,<2','fastapi','uvicorn','mss','Pillow','screeninfo','pywin32','keyboard','requests','psutil')

# ---------- write/update minimal modules (idempotent) ----------
# auto_utils.py
$auto_utils = @'
import os, re, time
def unique_path(base, stem, ext, width=3):
    i=0
    while True:
        s = f"{stem}_{i:0{width}d}{ext}" if i>0 else f"{stem}{ext}"
        p = os.path.join(base, s)
        if not os.path.exists(p): return p
        i += 1
'@
Write-Ascii (Join-Path $dev 'auto_utils.py') $auto_utils

# local_tools.py
$local_tools = @'
import os, json, time, ctypes
from mss import mss
from PIL import Image
from screeninfo import get_monitors
from .auto_utils import unique_path
import win32gui

def count_monitors():
    try:
        return {"monitors": len(get_monitors())}
    except Exception:
        return {"monitors": 1}

def _enum_windows():
    res=[]
    def cb(h, l):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowTextLength(h)>0:
            res.append(h)
        return True
    win32gui.EnumWindows(cb, None)
    return res

def count_windows():
    try:
        return {"windows": len(_enum_windows())}
    except Exception:
        return {"windows": 0}

def screenshot_autoname(root, stem='auto'):
    screens = os.path.join(root, 'reports','screens')
    os.makedirs(screens, exist_ok=True)
    path = unique_path(screens, stem, ".png")
    with mss() as sct:
        shot = sct.shot(output=path)
    return {"path": path}

def write_text_autoname(text):
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    path = unique_path(desktop, 'auto_probe', '.txt')
    with open(path, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(text)
    return {"path": path}
'@
Write-Ascii (Join-Path $dev 'local_tools.py') $local_tools

# tool_server.py
$tool_server = @'
from fastapi import FastAPI
from pydantic import BaseModel
from . import local_tools
from typing import Optional
app = FastAPI()

class WriteReq(BaseModel):
    text: str

@app.get("/monitors")
def monitors():
    return local_tools.count_monitors()

@app.get("/windows")
def windows():
    return local_tools.count_windows()

@app.get("/screenshot")
def screenshot(stem: Optional[str] = "auto"):
    return local_tools.screenshot_autoname(".", stem)

@app.post("/write")
def write(req: WriteReq):
    return local_tools.write_text_autoname(req.text)
'@
Write-Ascii (Join-Path $dev 'tool_server.py') $tool_server

# tail_utils.py (ASCII-safe append with shadow fallback)
$tail_utils = @'
import os, json, time
def append_tail(main_path, shadow_path, role, text):
    line = json.dumps({"ts": int(time.time()), "role": role, "text": text}, ensure_ascii=True)
    try:
        with open(main_path, "a", encoding="ascii", errors="ignore") as f:
            f.write(line + "\n")
        return True
    except Exception:
        try:
            with open(shadow_path, "a", encoding="ascii", errors="ignore") as f:
                f.write(line + "\n")
            return True
        except Exception:
            return False
'@
Write-Ascii (Join-Path $dev 'tail_utils.py') $tail_utils

# dispatcher.py
$dispatcher = @'
import os, re, json, time, requests
from .tail_utils import append_tail

ROOT = os.path.dirname(os.path.dirname(__file__))
TAIL = os.path.join(ROOT, "reports","chat","exact_tail.jsonl")
SHDW = os.path.join(ROOT, "reports","chat","exact_tail_shadow.jsonl")
EVT  = os.path.join(ROOT, "reports","DISPATCH_EVENTS.jsonl")
PORT = int(os.environ.get("TOOL_SERVER_PORT","8766"))

CALL_RE = re.compile(r"^\[ecosystem-call\]\s*(\{.*\})\s*$")

def log_event(obj):
    os.makedirs(os.path.join(ROOT,"reports"), exist_ok=True)
    with open(EVT, "a", encoding="ascii", errors="ignore") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")

def do_call(call):
    tool = call.get("tool")
    args = call.get("args") or {}
    try:
        if tool == "monitors":
            r = requests.get(f"http://127.0.0.1:{PORT}/monitors", timeout=5).json()
        elif tool == "windows":
            r = requests.get(f"http://127.0.0.1:{PORT}/windows", timeout=5).json()
        elif tool == "screenshot":
            stem = args.get("stem","auto")
            r = requests.get(f"http://127.0.0.1:{PORT}/screenshot", params={"stem": stem}, timeout=10).json()
        elif tool == "write":
            text = args.get("text","")
            r = requests.post(f"http://127.0.0.1:{PORT}/write", json={"text": text}, timeout=10).json()
        else:
            r = {"error": "unknown tool"}
    except Exception as e:
        r = {"error": str(e)}
    log_event({"call": call, "result": r})
    append_tail(TAIL, SHDW, "assistant", "[ecosystem-result] " + json.dumps(r, ensure_ascii=True))

def follow_tail():
    os.makedirs(os.path.dirname(TAIL), exist_ok=True)
    open(TAIL, "a").close()
    with open(TAIL, "r", encoding="ascii", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                time.sleep(0.3); f.seek(pos); continue
            line=line.strip()
            m = CALL_RE.match(line.split('text":',1)[-1][1:-1] if line.startswith('{') else line)
            if not m:
                if line.endswith("}") and "[ecosystem-call]" in line:
                    try:
                        js = json.loads(line)
                        txt = js.get("text","")
                        mm = CALL_RE.match(txt)
                        if mm:
                            call = json.loads(mm.group(1))
                            do_call(call)
                    except Exception:
                        pass
                continue
            try:
                call = json.loads(m.group(1))
                do_call(call)
            except Exception:
                log_event({"error":"parse", "line": line})

if __name__ == "__main__":
    follow_tail()
'@
Write-Ascii (Join-Path $dev 'dispatcher.py') $dispatcher

# nl_router.py
$nl_router = @'
import os, json, time
from .tail_utils import append_tail
try:
    from openai import OpenAI
except Exception:
    OpenAI=None

ROOT = os.path.dirname(os.path.dirname(__file__))
TAIL = os.path.join(ROOT, "reports","chat","exact_tail.jsonl")
SHDW = os.path.join(ROOT, "reports","chat","exact_tail_shadow.jsonl")
ROUT = os.path.join(ROOT, "reports","ROUTER_EVENTS.jsonl")

def log_event(obj):
    os.makedirs(os.path.join(ROOT,"reports"), exist_ok=True)
    with open(ROUT, "a", encoding="ascii", errors="ignore") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")

def basic_rule(text):
    t=text.lower()
    if "monitor" in t: return {"tool":"monitors","args":{}}
    if "window" in t:  return {"tool":"windows","args":{}}
    if "screenshot" in t: return {"tool":"screenshot","args":{"stem":"auto"}}
    if "write" in t or "note" in t: return {"tool":"write","args":{"text": text}}
    return None

def follow_tail():
    os.makedirs(os.path.dirname(TAIL), exist_ok=True)
    open(TAIL, "a").close()
    seen = 0
    while True:
        lines=[]
        with open(TAIL, "r", encoding="ascii", errors="ignore") as f:
            lines = f.readlines()
        if len(lines)>seen:
            for raw in lines[seen:]:
                try:
                    js=json.loads(raw)
                except Exception:
                    continue
                if js.get("role")=="user":
                    text=js.get("text","")
                    call = basic_rule(text)
                    if call is None and OpenAI:
                        try:
                            client=OpenAI()
                            r=client.chat.completions.create(model="gpt-5", max_completion_tokens=64, messages=[
                                {"role":"system","content":"Map the user request to a JSON with schema {tool: one of monitors|windows|screenshot|write, args: object}. If unsure, pick write with the same text."},
                                {"role":"user","content": text}
                            ])
                            tok=r.choices[0].message.content.strip()
                            call=json.loads(tok)
                        except Exception:
                            call={"tool":"write","args":{"text":text}}
                    if call:
                        append_tail(TAIL, SHDW, "assistant", "[ecosystem-call] "+json.dumps(call, ensure_ascii=True))
                        log_event({"from": text, "call": call})
            seen=len(lines)
        time.sleep(0.4)

if __name__=="__main__":
    follow_tail()
'@
Write-Ascii (Join-Path $dev 'nl_router.py') $nl_router

# tail_inject.py (robust appender via Python to avoid PS file locks)
$tail_inject = @'
import os, json, sys, time
ROOT = os.path.dirname(os.path.dirname(__file__))
TAIL = os.path.join(ROOT, 'reports','chat','exact_tail.jsonl')
os.makedirs(os.path.dirname(TAIL), exist_ok=True)
text = sys.argv[1] if len(sys.argv) > 1 else ''
line = json.dumps({"ts": int(time.time()), "role":"user", "text": text}, ensure_ascii=True)
with open(TAIL, 'a', encoding='ascii', errors='ignore') as f:
    f.write(line + '\n')
'@
Write-Ascii (Join-Path $dev 'tail_inject.py') $tail_inject


# ---------- start tool server + dispatcher + router ----------
$port = 8766
$toolLogOut = Join-Path $LOGS ('tool_server_{0}_out.log' -f $ts)
$toolLogErr = Join-Path $LOGS ('tool_server_{0}_err.log' -f $ts)
$dispLogOut = Join-Path $LOGS ('dispatcher_{0}_out.log' -f $ts)
$dispLogErr = Join-Path $LOGS ('dispatcher_{0}_err.log' -f $ts)
$routLogOut = Join-Path $LOGS ('router_{0}_out.log' -f $ts)
$routLogErr = Join-Path $LOGS ('router_{0}_err.log' -f $ts)

$env:TOOL_SERVER_PORT = "$port"
$env:MODEL_NAME = 'gpt-5'

$py = PythonExe
$tool = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','uvicorn','dev.tool_server:app','--host','127.0.0.1','--port',"$port") -WorkingDirectory $ROOT -RedirectStandardOutput $toolLogOut -RedirectStandardError $toolLogErr -WindowStyle Minimized
$disp = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','dev.dispatcher') -WorkingDirectory $ROOT -RedirectStandardOutput $dispLogOut -RedirectStandardError $dispLogErr -WindowStyle Minimized
$rout = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','dev.nl_router') -WorkingDirectory $ROOT -RedirectStandardOutput $routLogOut -RedirectStandardError $routLogErr -WindowStyle Minimized

$toolPid = 0; $dispPid = 0; $routPid = 0
if ($null -ne $tool) { try { $toolPid = [int]$tool.Id } catch {} }
if ($null -ne $disp)  { try { $dispPid = [int]$disp.Id } catch {} }
if ($null -ne $rout)  { try { $routPid = [int]$rout.Id } catch {} }
Write-Ascii $PIDS ("{`"tool`": "+$toolPid+", `"dispatch`": "+$dispPid+", `"router`": "+$routPid+", `"port`": "+$port+"}")

# ---------- seed natural-language user lines and verify ----------
function Add-User([string]$t){
  $py = PythonExe
  & $py (Join-Path $dev 'tail_inject.py') $t
}
function Wait-EventGrowth([int]$before,[int]$sec){
  $deadline=(Get-Date).AddSeconds($sec)
  $ev=Join-Path $REP 'DISPATCH_EVENTS.jsonl'
  while((Get-Date) -lt $deadline){
    $n = 0
    if (Test-Path $ev) {
      $n = (Get-Content $ev -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
    } else {
      $n = 0
    }
    if($n -gt $before){ return $true }
    Start-Sleep -Milliseconds 400
  }
  return $false
}

$before = 0
if (Test-Path (Join-Path $REP 'DISPATCH_EVENTS.jsonl')) { $before = (Get-Content (Join-Path $REP 'DISPATCH_EVENTS.jsonl') | Measure-Object -Line).Lines }
Add-User 'count my monitors'
$ok1 = Wait-EventGrowth -before $before -sec 20
$before = 0
if (Test-Path (Join-Path $REP 'DISPATCH_EVENTS.jsonl')) { $before = (Get-Content (Join-Path $REP 'DISPATCH_EVENTS.jsonl') | Measure-Object -Line).Lines }
Add-User 'write a short note to my desktop: ALL GREEN'
$ok2 = Wait-EventGrowth -before $before -sec 20
$before = 0
if (Test-Path (Join-Path $REP 'DISPATCH_EVENTS.jsonl')) { $before = (Get-Content (Join-Path $REP 'DISPATCH_EVENTS.jsonl') | Measure-Object -Line).Lines }
Add-User 'take a screenshot named auto'
$ok3 = Wait-EventGrowth -before $before -sec 20

# tail proof
$tailLines = (Get-Content $TAIL -Tail 200 -ErrorAction SilentlyContinue) + (Get-Content $SHDW -Tail 200 -ErrorAction SilentlyContinue)
$hasResult = $false
foreach($l in $tailLines){ if($l -match '\[ecosystem-result\]'){ $hasResult=$true; break } }

# write summary and bundle
$overall = $ok1 -and $ok2 -and $ok3 -and $hasResult
$sum = @(
  'AUTONOMOUS ULTIMATE SUMMARY',
  ('tool_server_port=' + $port),
  ('ok_monitors=' + $ok1),
  ('ok_write=' + $ok2),
  ('ok_screenshot=' + $ok3),
  ('tail_has_result=' + $hasResult),
  ('overall=' + $overall),
  ('pids_file=' + $PIDS)
) -join [Environment]::NewLine
Write-Ascii $OUT $sum

$bundle = Join-Path $RUNS ('autonomous_all_{0}' -f (TS))
Ensure-Dir $bundle
Copy-Item $OUT $bundle -Force
Copy-Item $TAIL $bundle -Force -ErrorAction SilentlyContinue
Copy-Item $SHDW $bundle -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $REP 'DISPATCH_EVENTS.jsonl') $bundle -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $REP 'ROUTER_EVENTS.jsonl')   $bundle -Force -ErrorAction SilentlyContinue
if(Test-Path $LOGS){ Copy-Item $LOGS $bundle -Recurse -Force -ErrorAction SilentlyContinue }
Compress-Archive -Path (Join-Path $bundle '*') -DestinationPath ($bundle + '.zip') -Force | Out-Null

Write-Host '=== AUTONOMOUS STACK ONLINE ==='
Write-Host ('Summary -> ' + $OUT)
Write-Host ('Bundle  -> ' + $bundle + '.zip')
