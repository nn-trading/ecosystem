param(
  [switch]$KeepRunning=$false,
  [int]$ToolPort=8765
)
$ErrorActionPreference='Stop'

#  Paths
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
New-Item -ItemType Directory -Force -Path $DEV,$CFG,$CFG2,$RPT,$CHAT,$SCR,$LOG,$LAR,$RAR | Out-Null
if (!(Test-Path (Join-Path $DEV '__init__.py'))) { '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '__init__.py') }

#  Dual-config write (handles builds expecting config\ or configs\)
$mdl="default: gpt-5`nlock: true"
$cms="mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl"
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG  'model.yaml') -Value $mdl
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG2 'model.yaml') -Value $mdl
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG  'comms.yaml') -Value $cms
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG2 'comms.yaml') -Value $cms
if (!(Test-Path $RT))  { '' | Set-Content -Encoding Ascii -LiteralPath $RT }
if (!(Test-Path $RTS)) { '' | Set-Content -Encoding Ascii -LiteralPath $RTS }

#  Python: autoname utils + tools
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

#  Tool server
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

#  Dispatcher (tail append with shadow fallback to beat file lock)
$dispatcher=@'
import json, time, re, http.client
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
SHDW = ROOT / "reports" / "chat" / "exact_tail_shadow.jsonl"
OUT  = ROOT / "reports" / "DISPATCH_EVENTS.jsonl"
MARK = re.compile(r"\[ecosystem-call\]\s*(\{.*\})", re.IGNORECASE)

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

def dispatch(call, host="127.0.0.1", port=8765):
    tool = call.get("tool"); args = call.get("args") or {}
    if tool == "monitors":   return http_get(host, port, "/monitors")
    if tool == "windows":    return http_get(host, port, "/windows")
    if tool == "screenshot": return http_post(host, port, "/screenshot", {"stem": args.get("stem","shot")})
    if tool == "write":      return http_post(host, port, "/write", {"stem": args.get("stem","note"), "text": args.get("text","OK")})
    if tool == "notepad":    return http_post(host, port, "/notepad", {"path": args.get("path","")})
    return {"error": f"unknown tool '{tool}'"}

def append_tail(obj):
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    try:
        with TAIL.open("a", encoding="utf-8") as f:
            f.write(line)
        return True
    except Exception:
        try:
            with SHDW.open("a", encoding="utf-8") as f:
                f.write(line)
            return True
        except Exception:
            return False

def follow(port=8765):
    seen = 0
    while True:
        try:
            lines = []
            if TAIL.exists():
                raw = TAIL.read_text(encoding="utf-8", errors="ignore").splitlines()
                if len(raw) > seen:
                    lines = raw[seen:]; seen = len(raw)
            for ln in lines:
                try:
                    obj = json.loads(ln); txt = str(obj.get("text",""))
                    m = MARK.search(txt)
                    if m:
                        call = json.loads(m.group(1))
                        res = dispatch(call, port=port)
                        OUT.parent.mkdir(parents=True, exist_ok=True)
                        OUT.open("a", encoding="utf-8").write(json.dumps({"call":call,"result":res})+"\n")
                        append_tail({"ts":time.time(),"role":"assistant","text":f"[ecosystem-result] {res}"})
                except Exception:
                    pass
            time.sleep(1)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    follow()
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'dispatcher.py') -Value $dispatcher

#  Self-seed one structured call (proves loop)
$selftest=@'
import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
seed = {"ts": time.time(), "role":"assistant", "text": '[ecosystem-call] {"tool":"write","args":{"stem":"auto_probe","text":"AUTONOMOUS OK"}}'}
TAIL.open("a", encoding="utf-8").write(json.dumps(seed, ensure_ascii=False)+"\n")
print("seeded")
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '_integration_selftest.py') -Value $selftest

#  Tail probe (accept tail, shadow, or dispatcher events)
$probe=@'
import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
SHDW = ROOT / "reports" / "chat" / "exact_tail_shadow.jsonl"
EVT  = ROOT / "reports" / "DISPATCH_EVENTS.jsonl"

def has_ok(p):
    if not p.exists(): return False
    for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines()[-400:]:
        try:
            obj=json.loads(ln)
            if obj.get("role")=="assistant" and str(obj.get("text","")).startswith("[ecosystem-result]"):
                return True
        except: pass
    return False

ok = has_ok(TAIL) or has_ok(SHDW)
if not ok and EVT.exists():
    for ln in EVT.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]:
        try:
            obj=json.loads(ln)
            if obj.get("call") and obj.get("result"): ok=True; break
        except: pass

print("OK" if ok else "NO")
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'tail_probe.py') -Value $probe

#  Venv + deps
$py=Join-Path $ROOT '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $ROOT '.venv') } else { python -m venv (Join-Path $ROOT '.venv') }
  $py=Join-Path $ROOT '.venv\Scripts\python.exe'
}
& $py -m pip -q install -U pip | Out-Null
& $py -m pip -q install fastapi uvicorn 'openai>=1,<2' mss pillow screeninfo pywin32 psutil requests | Out-Null

#  Stop any running ecosystem to release log locks, then rotate logs/tail
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
$ts=Get-Date -Format 'yyyyMMdd_HHmmss'
$std=Join-Path $LOG 'start_stdout.log'
$err=Join-Path $LOG 'start_stderr.log'
try { if(Test-Path $std){ Move-Item -Force $std (Join-Path $LAR ('start_stdout_'+$ts+'.log')) -ErrorAction Stop } } catch { try { Copy-Item -Force $std (Join-Path $LAR ('start_stdout_'+$ts+'.log')) -ErrorAction SilentlyContinue } catch {} }
try { if(Test-Path $err){ Move-Item -Force $err (Join-Path $LAR ('start_stderr_'+$ts+'.log')) -ErrorAction Stop } } catch { try { Copy-Item -Force $err (Join-Path $LAR ('start_stderr_'+$ts+'.log')) -ErrorAction SilentlyContinue } catch {} }
try { if(Test-Path $RT ){ Move-Item -Force $RT  (Join-Path $RAR ('exact_tail_'+$ts+'.jsonl')) -ErrorAction Stop } } catch { try { Copy-Item -Force $RT (Join-Path $RAR ('exact_tail_'+$ts+'.jsonl')) -ErrorAction SilentlyContinue } catch {} }
'' | Set-Content -Encoding Ascii -LiteralPath $RT
'' | Set-Content -Encoding Ascii -LiteralPath $RTS

#  Stop -> start headless; then bring up tools + dispatcher
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
Start-Sleep -Seconds 2

$toolArgs = @('-m','uvicorn','dev.tool_server:app','--host','127.0.0.1','--port',"$ToolPort",'--log-level','warning')
$toolProc = Start-Process -PassThru -FilePath $py -ArgumentList $toolArgs -WorkingDirectory $ROOT
$dispProc = Start-Process -PassThru -FilePath $py -ArgumentList @('-m','dev.dispatcher') -WorkingDirectory $ROOT

#  Seed + verify
& $py -m dev._integration_selftest | Out-Null
Start-Sleep -Seconds 3
$ok = (& $py -m dev.tail_probe) -match 'OK'

#  Stop background unless KeepRunning
if (-not $KeepRunning) {
  try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
  foreach($p in @($toolProc,$dispProc)){ try { if($p){ Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } } catch {} }
}

#  Bundle
$sum = @()
$sum += '[AUTONOMOUS v2] dual-config, shadow-tail fallback, dispatcher OK check.'
$sum += ('tail_probe_ok='+$ok)
$sum += ('tool_server_pid=' + $(if($toolProc){$toolProc.Id}else{'-'}))
$sum += ('dispatcher_pid=' + $(if($dispProc){$dispProc.Id}else{'-'}))
Set-Content -Encoding Ascii -LiteralPath (Join-Path $RPT 'AUTONOMOUS_INTEGRATION_V2.txt') -Value ($sum -join [Environment]::NewLine)

$bundle = Join-Path $ROOT ('runs\autonomous_integration_v2_'+$ts)
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach($p in @($RT,$RTS,(Join-Path $RPT 'AUTONOMOUS_INTEGRATION_V2.txt'),
                (Join-Path $LOG ('archive\start_stdout_'+$ts+'.log')),
                (Join-Path $LOG ('archive\start_stderr_'+$ts+'.log')),
                (Join-Path $ROOT 'reports\DISPATCH_EVENTS.jsonl'))){
  if(Test-Path $p){ Copy-Item -Force $p $bundle }
}
Compress-Archive -Force -Path (Join-Path $bundle '*') -DestinationPath (Join-Path $ROOT ('runs\autonomous_integration_v2_'+$ts+'.zip'))

Write-Host '=== AUTONOMOUS INTEGRATION v2 COMPLETE ==='
Write-Host ('Bundle: ' + (Join-Path $ROOT ('runs\autonomous_integration_v2_'+$ts+'.zip')))
Write-Host ('Tail result OK: ' + $ok)
if ($KeepRunning) { Write-Host 'Background: running; tool server + dispatcher left up.' } else { Write-Host 'Background: stopped.' }
