$ErrorActionPreference='Stop'
$root='C:\bots\ecosys'
$dev=Join-Path $root 'dev'
New-Item -ItemType Directory -Force -Path $dev, (Join-Path $root 'config'), (Join-Path $root 'reports\chat'), (Join-Path $root 'reports\screens'), (Join-Path $root 'logs\archive'), (Join-Path $root 'reports\archive\chat') | Out-Null
if(!(Test-Path (Join-Path $dev '__init__.py'))){ '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev '__init__.py') }

# config
Set-Content -Encoding Ascii -LiteralPath (Join-Path $root 'config\model.yaml') -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath (Join-Path $root 'config\comms.yaml') -Value "mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl"
if(!(Test-Path (Join-Path $root 'reports\chat\exact_tail.jsonl'))){ '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $root 'reports\chat\exact_tail.jsonl') }

# write autoname helpers (no typing into Notepad)
$auto_utils = @'
from pathlib import Path
import time
def unique_path(dirpath, stem, ext, limit=999):
    d=Path(dirpath); d.mkdir(parents=True, exist_ok=True)
    base=d/f"{stem}{ext}"
    if not base.exists(): return str(base)
    for i in range(1,limit+1):
        p=d/f"{stem}_{i:03d}{ext}"
        if not p.exists(): return str(p)
    return str(d/f"{stem}_{int(time.time())}{ext}")
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'auto_utils.py') -Value $auto_utils

$local_tools = @'
import os, subprocess, time
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
        def is_real(h):
            if not win32gui.IsWindowVisible(h): return False
            if not win32gui.GetWindowText(h): return False
            return True
        wins=[]
        def enum(h,_):
            if is_real(h): wins.append(h)
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
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'local_tools.py') -Value $local_tools

# gauntlet (no UI typing; autoname collision-proof)
$gauntlet = @'
import json, time
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
RPTS = Path(__file__).resolve().parents[1]/"reports"
RPTS.mkdir(parents=True, exist_ok=True)
(RPTS/"AUTONAME_OK.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'gauntlet_autoname.py') -Value $gauntlet

# probe tail for non-echo assistant lines after we seed it
$tail_probe = @'
import json, sys, time
from pathlib import Path
tail_path = Path(__file__).resolve().parents[1]/"reports"/"chat"/"exact_tail.jsonl"
deadline = time.time()+30
ok=False; found=[]
while time.time()<deadline:
    if tail_path.exists():
        lines = tail_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-500:]
        for ln in lines:
            try:
                o=json.loads(ln)
                if o.get("role")=="assistant" and o.get("text") and not str(o.get("text")).strip().lower().startswith("echo:"):
                    found.append(o["text"])
            except: pass
        if found:
            ok=True; break
    time.sleep(1)
print(json.dumps({"ok":ok,"examples":found[-3:]}))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'tail_probe.py') -Value $tail_probe

# ensure venv + deps
$py = Join-Path $root '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $root '.venv') } else { python -m venv (Join-Path $root '.venv') }
  $py = Join-Path $root '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --quiet mss pillow screeninfo pywin32 psutil requests 'openai>=1,<2' | Out-Null

# rotate logs/tail safely
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
if(Test-Path (Join-Path $root 'logs\start_stdout.log')){ Move-Item -Force (Join-Path $root 'logs\start_stdout.log') (Join-Path $root ('logs\archive\start_stdout_' + $ts + '.log')) }
if(Test-Path (Join-Path $root 'logs\start_stderr.log')){ Move-Item -Force (Join-Path $root 'logs\start_stderr.log') (Join-Path $root ('logs\archive\start_stderr_' + $ts + '.log')) }
if(Test-Path (Join-Path $root 'reports\chat\exact_tail.jsonl')){ Move-Item -Force (Join-Path $root 'reports\chat\exact_tail.jsonl') (Join-Path $root ('reports\archive\chat\exact_tail_' + $ts + '.jsonl')) }
'' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $root 'reports\chat\exact_tail.jsonl')

# stop -> start headless briefly, warm planner, seed tail, then stop again
try { powershell -NoProfile -File (Join-Path $root 'start.ps1') -Stop 1 | Out-Null } catch {}
powershell -NoProfile -File (Join-Path $root 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
Start-Sleep -Seconds 2
if(Test-Path (Join-Path $dev 'core02_planner.py')){ & $py (Join-Path $dev 'core02_planner.py') apply | Out-Null }
if(Test-Path (Join-Path $dev 'eco_cli.py')){ & $py (Join-Path $dev 'eco_cli.py') ask ping | Out-Null }
Start-Sleep -Seconds 2

# run autoname gauntlet (no typing) and tail probe
$ga = & $py -m dev.gauntlet_autoname
$tp = & $py -m dev.tail_probe

# stop background to leave system quiet
try { powershell -NoProfile -File (Join-Path $root 'start.ps1') -Stop 1 | Out-Null } catch {}

# write summary and bundle
$sum = @()
$sum += 'AUTONAME GAUNTLET OUTPUT:'
$sum += $ga
$sum += 'TAIL PROBE OUTPUT:'
$sum += $tp
Set-Content -Encoding Ascii -LiteralPath (Join-Path $root 'reports\AUTONAME_INTEGRATION_SUMMARY.txt') -Value ($sum -join [Environment]::NewLine)

$bundle = Join-Path $root ("runs\e2e_autoname_{0}" -f $ts)
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
Copy-Item -Force (Join-Path $root 'reports\AUTONAME_INTEGRATION_SUMMARY.txt') $bundle
Copy-Item -Force (Join-Path $root 'reports\AUTONAME_OK.json') $bundle -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $root 'reports\chat\exact_tail.jsonl') $bundle -ErrorAction SilentlyContinue
$stdoutArc = Join-Path $root ("logs\archive\start_stdout_{0}.log" -f $ts)
$stderrArc = Join-Path $root ("logs\archive\start_stderr_{0}.log" -f $ts)
if(Test-Path $stdoutArc){ Copy-Item -Force $stdoutArc $bundle }
if(Test-Path $stderrArc){ Copy-Item -Force $stderrArc $bundle }
Compress-Archive -Force -Path (Join-Path $bundle '*') -DestinationPath (Join-Path $root ("runs\e2e_autoname_{0}.zip" -f $ts))
