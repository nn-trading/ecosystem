param(
  [switch]$KeepRunning=$false,
  [int]$ToolPort=8765
)
$ErrorActionPreference='Stop'

#  Paths/dirs 
$ROOT=(Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).Parent.FullName
$DEV =Join-Path $ROOT 'dev'
$CFG =Join-Path $ROOT 'config'
$RPT =Join-Path $ROOT 'reports'
$RT  =Join-Path $RPT  'chat\exact_tail.jsonl'
$SCR =Join-Path $RPT  'screens'
$LOG =Join-Path $ROOT 'logs'
$LAR =Join-Path $LOG  'archive'
$RAR =Join-Path $ROOT 'reports\archive\chat'
New-Item -ItemType Directory -Force -Path $DEV,$CFG,$RPT,$SCR,$LOG,$LAR,$RAR,(Join-Path $RPT 'chat') | Out-Null
if (!(Test-Path (Join-Path $DEV '__init__.py'))) { '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '__init__.py') }

#  Configs (autonomous; model locked but configurable in file) 
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'model.yaml')  -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'comms.yaml')  -Value "mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl"
if (!(Test-Path $RT)) { '' | Set-Content -Encoding Ascii -LiteralPath $RT }

#  Python modules: autoname utils + local tools 
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

#  Tool Server (HTTP) for planner/brain to call via JSON (no hardcoding) 
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

#  Dispatcher: watches tail for structured calls & executes tools autonomously 
$dispatcher=@'
import json, time, re, threading, http.client
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
OUT  = ROOT / "reports" / "DISPATCH_EVENTS.jsonl"
MARK = re.compile(r"\[ecosystem-call\]\s*(\{.*\})", re.IGNORECASE)

def http_post(host, port, path, payload):
    conn = http.client.HTTPConnection(host, port, timeout=8)
    body = json.dumps(payload)
    headers = {"Content-Type":"application/json"}
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    try:
        return json.loads(data.decode("utf-8","ignore"))
    except:
        return {"status": resp.status, "raw": data.decode("utf-8","ignore")}

def http_get(host, port, path):
    conn = http.client.HTTPConnection(host, port, timeout=8)
    conn.request("GET", path)
    resp = conn.getresponse()
    data = resp.read()
    try:
        return json.loads(data.decode("utf-8","ignore"))
    except:
        return {"status": resp.status, "raw": data.decode("utf-8","ignore")}

def dispatch(call, host="127.0.0.1", port=8765):
    tool = call.get("tool")
    args = call.get("args") or {}
    if tool == "monitors":
        return http_get(host, port, "/monitors")
    if tool == "windows":
        return http_get(host, port, "/windows")
    if tool == "screenshot":
        return http_post(host, port, "/screenshot", {"stem": args.get("stem","shot")})
    if tool == "write":
        return http_post(host, port, "/write", {"stem": args.get("stem","note"), "text": args.get("text","OK")})
    if tool == "notepad":
        return http_post(host, port, "/notepad", {"path": args.get("path","")})
    return {"error": f"unknown tool '{tool}'"}

def tail_follow(port=8765):
    seen = 0
    while True:
        try:
            lines = []
            if TAIL.exists():
                raw = TAIL.read_text(encoding="utf-8", errors="ignore").splitlines()
                if len(raw) > seen:
                    lines = raw[seen:]
                    seen = len(raw)
            for ln in lines:
                try:
                    obj = json.loads(ln)
                    txt = str(obj.get("text",""))
                    m = MARK.search(txt)
                    if m:
                        call = json.loads(m.group(1))
                        res = dispatch(call, port=port)
                        OUT.parent.mkdir(parents=True, exist_ok=True)
                        OUT.open("a", encoding="utf-8").write(json.dumps({"call":call,"result":res})+"\n")
                        # append an assistant line to tail so the ecosystem sees outcome
                        TAIL.open("a", encoding="utf-8").write(json.dumps({"ts":time.time(),"role":"assistant","text":f"[ecosystem-result] {res}"})+"\n")
                except Exception:
                    pass
            time.sleep(1)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    tail_follow()
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'dispatcher.py') -Value $dispatcher

#  Brain hint: lightweight system prompt fragment (no hardcoding actions) 
$hint=@'
When you decide an OS action is useful, emit a line containing:
[ecosystem-call] {"tool":"screenshot","args":{"stem":"work"}}
Supported tools: "monitors","windows","screenshot","write","notepad".
Prefer short steps. After executing, expect a follow-up "[ecosystem-result] {...}".
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'brain_hint.txt') -Value $hint

#  Self-test: seed a synthetic call so dispatcher proves autonomy 
$selftest=@'
import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
seed = {"ts": time.time(), "role":"assistant", "text": '[ecosystem-call] {"tool":"write","args":{"stem":"auto_probe","text":"AUTONOMOUS OK"}}'}
TAIL.open("a", encoding="utf-8").write(json.dumps(seed)+"\n")
print("seeded")
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '_integration_selftest.py') -Value $selftest

#  Ensure venv/deps 
$py=Join-Path $ROOT '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $ROOT '.venv') } else { python -m venv (Join-Path $ROOT '.venv') }
  $py=Join-Path $ROOT '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --quiet fastapi uvicorn 'openai>=1,<2' mss pillow screeninfo pywin32 psutil requests | Out-Null

#  Clean rotate logs & tail 
$ts=Get-Date -Format 'yyyyMMdd_HHmmss'
$std=Join-Path $LOG 'start_stdout.log'
$err=Join-Path $LOG 'start_stderr.log'
if(Test-Path $std){ Move-Item -Force $std (Join-Path $LAR ('start_stdout_'+$ts+'.log')) }
if(Test-Path $err){ Move-Item -Force $err (Join-Path $LAR ('start_stderr_'+$ts+'.log')) }
if(Test-Path $RT ){ Move-Item -Force $RT  (Join-Path $RAR ('exact_tail_'+$ts+'.jsonl')) }
'' | Set-Content -Encoding Ascii -LiteralPath $RT

#  Stop -> start headless briefly to seed tail, then bring up Tool Server & Dispatcher 
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
Start-Sleep -Seconds 2

# Tool server
$toolArgs = @('-m','uvicorn','dev.tool_server:app','--host','127.0.0.1','--port',"$ToolPort",'--log-level','warning')
$toolProc = Start-Process -PassThru -FilePath $py -ArgumentList $toolArgs -WorkingDirectory $ROOT

# Wait for tool server to become healthy before seeding
$healthy = $false
for($i=0; $i -lt 30; $i++){
  try {
    $resp = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/monitors" -f $ToolPort) -UseBasicParsing -TimeoutSec 2
    if($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500){ $healthy=$true; break }
  } catch {}
  Start-Sleep -Milliseconds 300
}

# Dispatcher (watches tail and acts)
$dispArgs = @('-m','dev.dispatcher')
$dispProc = Start-Process -PassThru -FilePath $py -ArgumentList $dispArgs -WorkingDirectory $ROOT

# Seed one structured call; dispatcher should handle it and echo a result back into tail
& $py -m dev._integration_selftest | Out-Null
Start-Sleep -Seconds 5

# Verify dispatcher wrote result
$tp = Get-Content $RT -Tail 200 | ForEach-Object { try { $_ | ConvertFrom-Json } catch {} } |
  Where-Object { $_ -and $_.role -eq 'assistant' -and $_.text -like '[ecosystem-result]*' } |
  Select-Object -Last 1
$ok = $false
if ($tp) { $ok = $true }

# Stop background unless requested to keep running
if (-not $KeepRunning) {
  try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
  try { if ($toolProc) { Stop-Process -Id $toolProc.Id -Force -ErrorAction SilentlyContinue } } catch {}
  try { if ($dispProc) { Stop-Process -Id $dispProc.Id -Force -ErrorAction SilentlyContinue } } catch {}
}

# Summary + bundle
$sum=@()
$sum += '[AUTONOMOUS INTEGRATION] Tool Server + Dispatcher wired; structured calls executable.'
$sum += ('tool_server_pid=' + ($toolProc.Id))
$sum += ('dispatcher_pid=' + ($dispProc.Id))
$sum += ('tail_probe_ok=' + $ok)
Set-Content -Encoding Ascii -LiteralPath (Join-Path $RPT 'AUTONOMOUS_INTEGRATION_SUMMARY.txt') -Value ($sum -join [Environment]::NewLine)

$bundle = Join-Path $ROOT ('runs\autonomous_integration_'+$ts)
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
Copy-Item -Force $RT $bundle
Copy-Item -Force (Join-Path $RPT 'AUTONOMOUS_INTEGRATION_SUMMARY.txt') $bundle
if (Test-Path (Join-Path $LAR ('start_stdout_'+$ts+'.log'))) { Copy-Item -Force (Join-Path $LAR ('start_stdout_'+$ts+'.log')) $bundle }
if (Test-Path (Join-Path $LAR ('start_stderr_'+$ts+'.log'))) { Copy-Item -Force (Join-Path $LAR ('start_stderr_'+$ts+'.log')) $bundle }
Compress-Archive -Force -Path (Join-Path $bundle '*') -DestinationPath (Join-Path $ROOT ('runs\autonomous_integration_'+$ts+'.zip'))

Write-Host '=== AUTONOMOUS INTEGRATION COMPLETE ==='
Write-Host ('Bundle: ' + (Join-Path $ROOT ('runs\autonomous_integration_'+$ts+'.zip')))
Write-Host ('Tail result OK: ' + $ok)
if ($KeepRunning) { Write-Host 'Background: running; tool server + dispatcher left up.' } else { Write-Host 'Background: stopped; processes terminated.' }
