param(
  [switch]$LaunchChat=$false,
  [switch]$KeepRunning=$false
)
$ErrorActionPreference='Stop'

# --- Paths & dirs ---
$ROOT = (Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).Parent.FullName
$DEV  = Join-Path $ROOT 'dev'
$CFG  = Join-Path $ROOT 'config'
$RPT  = Join-Path $ROOT 'reports'
$TAIL = Join-Path $RPT  'chat\exact_tail.jsonl'
$SCR  = Join-Path $RPT  'screens'
$LOG  = Join-Path $ROOT 'logs'
$LARCH= Join-Path $LOG  'archive'
$RARCH= Join-Path $ROOT 'reports\archive\chat'
New-Item -ItemType Directory -Force -Path $DEV,$CFG,$RPT,$SCR,$LOG,$LARCH,$RARCH,(Join-Path $RPT 'chat') | Out-Null
if (!(Test-Path (Join-Path $DEV '__init__.py'))) { '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '__init__.py') }

# --- Configs (no brittle in-code constants; live in files) ---
# Model lock can be flipped later by editing config\model.yaml
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'model.yaml') -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'comms.yaml') -Value "mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl"
if (!(Test-Path $TAIL)) { '' | Set-Content -Encoding Ascii -LiteralPath $TAIL }

# --- Python: autoname utilities & local tools (no typing, no Save As) ---
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
import os, subprocess, time, json
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
        def ok(h):
            return win32gui.IsWindowVisible(h) and bool(win32gui.GetWindowText(h))
        wins=[]
        def enum(h,_):
            if ok(h): wins.append(h)
        win32gui.EnumWindows(enum, None)
        return {"windows": len(wins)}
    except Exception as e:
        return {"windows": 0, "error": str(e)}

def screenshot_autoname(stem="e2e"):
    from mss import mss
    p = (RPTS/"screens"/f"{stem}_{time.strftime('%Y%m%d_%H%M%S')}.png")
    with mss() as s: s.shot(output=str(p))
    return str(p)

def write_text_file_autoname(text="E2E NOTEPAD OK", stem="e2e_notepad"):
    p = Path(unique_path(DESK, stem, ".txt"))
    p.write_text(text, encoding="utf-8")
    return str(p)

def write_probe_autoname(stem="e2e_probe", text="OK"):
    p = Path(unique_path(DESK, stem, ".txt"))
    p.write_text(text, encoding="utf-8")
    return str(p)

def open_notepad(path):
    try:
        subprocess.Popen(["notepad.exe", str(path)])
        return True
    except Exception:
        return False
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'local_tools.py') -Value $local_tools

$gauntlet=@'
import json
from pathlib import Path
from .local_tools import (
  write_text_file_autoname, write_probe_autoname,
  screenshot_autoname, count_monitors, count_windows
)
res={}
res["monitors"]=count_monitors()
res["windows"]=count_windows()
res["notepad1"]=write_text_file_autoname("E2E NOTEPAD OK","e2e_notepad")
res["notepad2"]=write_text_file_autoname("E2E NOTEPAD OK","e2e_notepad")
res["desk1"]=write_probe_autoname("e2e_probe","OK")
res["desk2"]=write_probe_autoname("e2e_probe","OK")
res["screenshot"]=screenshot_autoname("e2e")
ok=True
try:
  from pathlib import Path as P
  if P(res["notepad1"]).name==P(res["notepad2"]).name: ok=False
  if P(res["desk1"]).name==P(res["desk2"]).name: ok=False
except Exception: ok=False
out={"ok":ok,"artifacts":res}
(R := (Path(__file__).resolve().parents[1]/"reports"/"AUTONAME_OK.json")).write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'gauntlet_autoname.py') -Value $gauntlet

$tail_probe=@'
import json, time
from pathlib import Path
tail = Path(__file__).resolve().parents[1]/"reports"/"chat"/"exact_tail.jsonl"
deadline = time.time()+30
found=[]
while time.time()<deadline:
    if tail.exists():
        for ln in tail.read_text(encoding="utf-8",errors="ignore").splitlines()[-500:]:
            try:
                o=json.loads(ln)
                if o.get("role")=="assistant" and o.get("text") and not str(o["text"]).strip().lower().startswith("echo:"):
                    found.append(o["text"])
            except: pass
        if found: break
    time.sleep(1)
print(json.dumps({"ok": bool(found), "examples": found[-3:]}))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'tail_probe.py') -Value $tail_probe

# --- Ensure venv + deps (no version pin beyond API major) ---
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if (!(Test-Path $py)) {
  if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv (Join-Path $ROOT '.venv') } else { python -m venv (Join-Path $ROOT '.venv') }
  $py = Join-Path $ROOT '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --quiet mss pillow screeninfo pywin32 psutil requests 'openai>=1,<2' | Out-Null

# --- Rotate logs/tail for clean run ---
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$std = Join-Path $LOG 'start_stdout.log'
$err = Join-Path $LOG 'start_stderr.log'
if (Test-Path $std) { Move-Item -Force $std (Join-Path $LARCH ('start_stdout_'+$ts+'.log')) }
if (Test-Path $err) { Move-Item -Force $err (Join-Path $LARCH ('start_stderr_'+$ts+'.log')) }
if (Test-Path $TAIL){ Move-Item -Force $TAIL (Join-Path $RARCH ('exact_tail_'+$ts+'.jsonl')) }
'' | Set-Content -Encoding Ascii -LiteralPath $TAIL

# --- Stop -> start headless briefly, warm planner, seed tail ---
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
Start-Sleep -Seconds 2
if (Test-Path (Join-Path $DEV 'core02_planner.py')) { & $py (Join-Path $DEV 'core02_planner.py') apply | Out-Null }
if (Test-Path (Join-Path $DEV 'eco_cli.py'))       { & $py (Join-Path $DEV 'eco_cli.py') ask ping | Out-Null }
Start-Sleep -Seconds 2

# --- Run autoname gauntlet + tail probe ---
$ga = & $py -m dev.gauntlet_autoname
$tp = & $py -m dev.tail_probe

# --- Optional chat launch (user-controlled) ---
if ($LaunchChat) {
  $shells = @(
    @{mod='dev.brain_chat_shell'; file=(Join-Path $DEV 'brain_chat_shell.py')},
    @{mod='dev.chat_shell';      file=(Join-Path $DEV 'chat_shell.py')}
  )
  $launched=$false
  foreach($s in $shells){
    if ($launched) { break }
    if (Test-Path $s.file){ Start-Process $py -ArgumentList @('-m',$s.mod); $launched=$true }
  }
}

# --- Stop background unless KeepRunning requested ---
if (-not $KeepRunning) {
  try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
}

# --- Summaries + bundle ---
$sum = @()
$sum += '[AUTONOMOUS STACK] GPT-5 lock, headless bring-up, gauntlet, tail-probe complete.'
$sum += 'GAUNTLET:'; $sum += $ga
$sum += 'TAIL_PROBE:'; $sum += $tp
Set-Content -Encoding Ascii -LiteralPath (Join-Path $RPT 'AUTONOMOUS_STACK_SUMMARY.txt') -Value ($sum -join [Environment]::NewLine)

$bundle = Join-Path $ROOT ('runs\autonomous_stack_'+$ts)
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
Copy-Item -Force $TAIL $bundle -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $RPT 'AUTONOMOUS_STACK_SUMMARY.txt') $bundle
Copy-Item -Force (Join-Path $RPT 'AUTONAME_OK.json') $bundle -ErrorAction SilentlyContinue
if (Test-Path (Join-Path $LARCH ('start_stdout_'+$ts+'.log'))) { Copy-Item -Force (Join-Path $LARCH ('start_stdout_'+$ts+'.log')) $bundle }
if (Test-Path (Join-Path $LARCH ('start_stderr_'+$ts+'.log'))) { Copy-Item -Force (Join-Path $LARCH ('start_stderr_'+$ts+'.log')) $bundle }
Compress-Archive -Force -Path (Join-Path $bundle '*') -DestinationPath (Join-Path $ROOT ('runs\autonomous_stack_'+$ts+'.zip'))

Write-Host '=== AUTONOMOUS STACK COMPLETE ==='
Write-Host ('Bundle: ' + (Join-Path $ROOT ('runs\autonomous_stack_'+$ts+'.zip')))
if ($LaunchChat) { Write-Host 'Chat: launched' } else { Write-Host 'Chat: not launched' }
if ($KeepRunning) { Write-Host 'Background: running' } else { Write-Host 'Background: stopped' }
