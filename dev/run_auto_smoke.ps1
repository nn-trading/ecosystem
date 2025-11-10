$ErrorActionPreference='Stop'
$root='C:\bots\ecosys'
$dev=Join-Path $root 'dev'
if(!(Test-Path $dev)){ New-Item -ItemType Directory -Force -Path $dev|Out-Null }
Set-Location -LiteralPath $root
if(!(Test-Path (Join-Path $dev '__init__.py'))){ '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev '__init__.py') }

# --- auto_utils.py (global autoname helper) ---
$py1=@'
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
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'auto_utils.py') -Value $py1

# --- local_tools.py (uses autoname everywhere) ---
$py2=@'
import os, time, subprocess
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
        def enum(h, _): 
            if is_real(h): wins.append(h)
        win32gui.EnumWindows(enum, None)
        return {"windows": len(wins)}
    except Exception as e:
        return {"windows": 0, "error": str(e)}

def screenshot_autoname(stem='e2e'):
    from mss import mss
    p = (RPTS/'screens'/f"{stem}_{time.strftime('%Y%m%d_%H%M%S')}.png")
    with mss() as s: s.shot(output=str(p))
    return str(p)

def desktop_write_autoname(text='OK', stem='note'):
    p = Path(unique_path(DESK, stem, '.txt'))
    p.write_text(text, encoding='utf-8'); return str(p)

def notepad_save_text_autoname(text='E2E NOTEPAD OK', stem='e2e_notepad'):
    import pyautogui as pg, time
    p = subprocess.Popen(['notepad.exe']); time.sleep(1.2)
    pg.typewrite(text, interval=0.02)
    def try_save(path):
        pg.hotkey('ctrl','s'); time.sleep(0.5)
        pg.typewrite(path, interval=0.01); time.sleep(0.2)
        pg.press('enter'); time.sleep(0.8)
        return Path(path).exists()
    target = unique_path(DESK, stem, '.txt')
    for _ in range(4):
        if try_save(target): break
        target = unique_path(DESK, stem, '.txt')
    try: pg.hotkey('alt','f4')
    except: pass
    try: p.terminate()
    except: pass
    return target if Path(target).exists() else None
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'local_tools.py') -Value $py2

# --- smoke: proves autoname works & writes artifacts ---
$py3=@'
import json
from pathlib import Path
from .local_tools import (
    count_monitors, count_windows,
    screenshot_autoname, desktop_write_autoname,
    notepad_save_text_autoname
)
ROOT=Path(__file__).resolve().parents[1]; RPTS=ROOT/'reports'
RPTS.mkdir(parents=True, exist_ok=True)
out={}
out['monitors']=count_monitors(); out['windows']=count_windows()
out['desktop_write']=desktop_write_autoname('OK','e2e_probe')
out['notepad_saved']=notepad_save_text_autoname('E2E NOTEPAD OK','e2e_notepad')
out['screenshot']=screenshot_autoname('e2e')
(RPTS/'AUTONAME_OK.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'auto_smoke.py') -Value $py3

# --- ensure venv + deps ---
$py=Join-Path $root '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $root '.venv') } else { python -m venv (Join-Path $root '.venv') }
  $py=Join-Path $root '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --quiet pyautogui pywin32 mss pillow screeninfo requests psutil 'openai>=1,<2' | Out-Null

# --- run smoke, then your E2E harness if present ---
& $py -m dev.auto_smoke
$e2e=Join-Path $dev 'oh_end2end.ps1'
if(Test-Path $e2e){ powershell -NoProfile -ExecutionPolicy Bypass -File $e2e }
