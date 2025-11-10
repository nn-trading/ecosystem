$ErrorActionPreference='Stop'
$root='C:\bots\ecosys'
$dev=Join-Path $root 'dev'
New-Item -ItemType Directory -Force -Path $dev, (Join-Path $root 'reports'), (Join-Path $root 'reports\screens') | Out-Null
if(!(Test-Path (Join-Path $dev '__init__.py'))){ '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev '__init__.py') }

$auto_utils = @'
from pathlib import Path
import time
def unique_path(dirpath, stem, ext, limit=999):
    d=Path(dirpath); d.mkdir(parents=True, exist_ok=True)
    base=d/f"{stem}{ext}"
    if not base.exists(): return str(base)
    for i in range(1,limit+1):
        c=d/f"{stem}_{i:03d}{ext}"
        if not c.exists(): return str(c)
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

def open_notepad(path):
    try:
        subprocess.Popen(["notepad.exe", str(path)])
        return True
    except Exception:
        return False
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'local_tools.py') -Value $local_tools

$smoke = @'
import json
from pathlib import Path
from .local_tools import (
    write_text_file_autoname, open_notepad,
    screenshot_autoname, count_monitors, count_windows
)

res={}
res["monitors"]=count_monitors()
res["windows"]=count_windows()

# create two different files without any UI typing
res["notepad1"]=write_text_file_autoname("E2E NOTEPAD OK", "e2e_notepad")
res["notepad2"]=write_text_file_autoname("E2E NOTEPAD OK", "e2e_notepad")

# optional: just show the first file (no typing)
try:
    open_notepad(res["notepad1"])
except Exception:
    pass

# two desktop probes with unique names too
from .auto_utils import unique_path
desk = Path.home() / "Desktop"
p3 = Path(unique_path(desk, "e2e_probe", ".txt"))
p3.write_text("OK", encoding="utf-8"); res["desk1"]=str(p3)
p4 = Path(unique_path(desk, "e2e_probe", ".txt"))
p4.write_text("OK", encoding="utf-8"); res["desk2"]=str(p4)

res["screenshot"]=screenshot_autoname("e2e")

ok=True
try:
    if Path(res["notepad1"]).name == Path(res["notepad2"]).name: ok=False
    if Path(res["desk1"]).name == Path(res["desk2"]).name: ok=False
except Exception:
    ok=False

out={"ok": ok, "artifacts": res}
RPTS = Path(__file__).resolve().parents[1]/"reports"
RPTS.mkdir(parents=True, exist_ok=True)
(RPTS/"AUTONAME_OK.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'auto_smoke_no_typing.py') -Value $smoke

$py = Join-Path $root '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $root '.venv') } else { python -m venv (Join-Path $root '.venv') }
  $py = Join-Path $root '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --quiet mss pillow screeninfo pywin32 psutil requests 'openai>=1,<2' | Out-Null

& $py -m dev.auto_smoke_no_typing
