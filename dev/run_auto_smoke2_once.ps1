$ErrorActionPreference='Stop'
$root='C:\bots\ecosys'
$dev=Join-Path $root 'dev'
New-Item -ItemType Directory -Force -Path $dev, (Join-Path $root 'reports'), (Join-Path $root 'reports\screens') | Out-Null
if(!(Test-Path (Join-Path $dev '__init__.py'))){ '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev '__init__.py') }

# --- auto_utils.py ---
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

# --- local_tools.py (launches Notepad WITH a unique path; no Save As needed) ---
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

def desktop_write_autoname(text="OK", stem="note"):
    p = Path(unique_path(DESK, stem, ".txt"))
    p.write_text(text, encoding="utf-8"); return str(p)

def notepad_save_text_autoname(text="E2E NOTEPAD OK", stem="e2e_notepad"):
    import pyautogui as pg
    # Pre-compute a guaranteed-new path and launch Notepad with it
    target = Path(unique_path(DESK, stem, ".txt"))
    p = subprocess.Popen(["notepad.exe", str(target)])
    time.sleep(1.2)
    try:
        # Replace any default content, then save (file already bound to unique path)
        pg.hotkey("ctrl","a"); time.sleep(0.05)
        pg.typewrite(text, interval=0.02); time.sleep(0.1)
        pg.hotkey("ctrl","s"); time.sleep(0.5)
    except Exception:
        pass

    # Extremely defensive fallback if an overwrite dialog somehow appears
    try:
        import win32gui
        hwnd = win32gui.FindWindow(None, "Confirm Save As")
        if hwnd:
            # Press 'N' (No), then Save As to a fresh unique name
            pg.press("n"); time.sleep(0.4)
            pg.hotkey("ctrl","shift","s"); time.sleep(0.6)
            newt = Path(unique_path(DESK, stem, ".txt"))
            pg.typewrite(str(newt)); time.sleep(0.2); pg.press("enter"); time.sleep(0.6)
            target = newt
    except Exception:
        pass

    # Close Notepad politely
    try:
        pg.hotkey("alt","f4"); time.sleep(0.3)
        pg.press("y")  # if prompted to save
    except Exception:
        pass
    return str(target) if Path(target).exists() else None
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'local_tools.py') -Value $py2

# --- auto_smoke2.py (double save) ---
$py3=@'
import json, time
from pathlib import Path
from .local_tools import (
    notepad_save_text_autoname, desktop_write_autoname,
    screenshot_autoname, count_monitors, count_windows
)

res={}
res["monitors"]=count_monitors()
res["windows"]=count_windows()
res["notepad1"]=notepad_save_text_autoname("E2E NOTEPAD OK","e2e_notepad")
time.sleep(0.8)
res["notepad2"]=notepad_save_text_autoname("E2E NOTEPAD OK","e2e_notepad")
res["desk1"]=desktop_write_autoname("OK","e2e_probe")
res["desk2"]=desktop_write_autoname("OK","e2e_probe")
res["screenshot"]=screenshot_autoname("e2e")

ok=True
try:
    if not res["notepad1"] or not res["notepad2"]: ok=False
    else:
        p1=Path(res["notepad1"]); p2=Path(res["notepad2"])
        if p1.exists() and p2.exists() and p1.name==p2.name: ok=False
    if res["desk1"] and res["desk2"] and Path(res["desk1"]).name==Path(res["desk2"]).name: ok=False
except Exception:
    ok=False

out={"ok": ok, "artifacts": res}
RPTS=Path(__file__).resolve().parents[1]/"reports"
RPTS.mkdir(parents=True, exist_ok=True)
(RPTS/"AUTONAME_OK.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $dev 'auto_smoke2.py') -Value $py3

# --- ensure venv + deps ---
$py=Join-Path $root '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $root '.venv') } else { python -m venv (Join-Path $root '.venv') }
  $py=Join-Path $root '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --quiet pyautogui pywin32 mss pillow screeninfo psutil requests 'openai>=1,<2' | Out-Null

# --- run the double-save smoke ---
& $py -m dev.auto_smoke2
