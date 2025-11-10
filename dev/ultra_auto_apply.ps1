param()
$ErrorActionPreference='Stop'
$root='C:\bots\ecosys'; if(!(Test-Path $root)){ throw 'C:\bots\ecosys not found' }
Set-Location $root
New-Item -ItemType Directory -Force -Path .\dev,.\configs,.\reports\chat,.\reports\screens | Out-Null

# Ensure dev package marker for module imports
if (!(Test-Path '.\dev\__init__.py')) { '' | Set-Content -Encoding Ascii -LiteralPath '.\dev\__init__.py' }

# --- venv + deps (desktop control) ---
$py = '.\.venv\Scripts\python.exe'
if(-not (Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv .venv } else { python -m venv .venv }
}
& $py -m pip -q install --upgrade pip
& $py -m pip -q install openai==1.* pyautogui pywin32 mss pillow screeninfo keyboard requests psutil

# --- model lock to GPT-5 (no switching) ---
@'
default: gpt-5
lock: true
'@ | Set-Content -Encoding Ascii -LiteralPath .\configs\model.yaml

# --- local autonomy tools (generic; no hardcoded tasks) ---
$lt = @'
import os, time, json, ctypes, subprocess, pathlib, math, requests
from typing import List, Dict
ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SCREENS = REPORTS / "screens"; SCREENS.mkdir(parents=True, exist_ok=True)
DESK = pathlib.Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))

# Desktop control libs
import pyautogui, mss, PIL.Image # type: ignore
pyautogui.FAILSAFE = False

# Window enumeration via Win32
import win32gui, win32con  # type: ignore

def _is_visible(hwnd): return win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd).strip()!=""

def list_window_titles() -> List[str]:
    titles=[]
    def cb(hwnd, extra):
        if _is_visible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if t: titles.append(t)
    win32gui.EnumWindows(cb, None)
    return titles

def count_windows() -> int:
    return len(list_window_titles())

def count_monitors() -> int:
    try:
        import screeninfo  # type: ignore
        return len(screeninfo.get_monitors())
    except Exception:
        # fallback using mss
        with mss.mss() as s: return len(s.monitors)-1

def screenshot(name: str|None=None) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = name or f"screen_{ts}.png"
    path = SCREENS / fname
    with mss.mss() as s:
        shot = s.grab(s.monitors[1])  # primary
        img = PIL.Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img.save(str(path))
    return str(path)

def open_app(cmd: str):
    subprocess.Popen(cmd, shell=True)

def focus_window(title_part: str, timeout=5.0) -> bool:
    t0=time.time()
    while time.time()-t0<timeout:
        found=[]
        def cb(hwnd, extra):
            if _is_visible(hwnd):
                t=win32gui.GetWindowText(hwnd)
                if title_part.lower() in t.lower():
                    found.append(hwnd)
        win32gui.EnumWindows(cb, None)
        if found:
            hwnd=found[0]
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        time.sleep(0.2)
    return False

def type_text(text: str, interval=0.02):
    pyautogui.typewrite(text, interval=interval)

def keys(seq: str):
    # e.g. "ctrl+s", "alt+tab", "enter", "esc"
    parts = [p.strip() for p in seq.lower().split('+')]
    if len(parts)>1:
        pyautogui.hotkey(*parts)
    else:
        k = parts[0]
        if k in ("enter","esc","tab","backspace","delete","space"):
            pyautogui.press(k)
        else:
            pyautogui.typewrite(parts[0])

def mouse_move(x:int,y:int): pyautogui.moveTo(int(x),int(y),duration=0)

def click(): pyautogui.click()

# Generic forecast to Desktop for ANY city + N days using Open-Meteo (geocoding + forecast)

def forecast_to_desktop(city: str, days: int=3) -> List[str]:
    city = city.strip()
    days = max(1, min(int(days), 7))
    g = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name":city,"count":1}).json()
    if not g.get("results"): raise RuntimeError(f"city not found: {city}")
    lat=g["results"][0]["latitude"]; lon=g["results"][0]["longitude"]
    f = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude":lat,"longitude":lon,
        "daily":"weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days":days,"timezone":"auto"
    }).json()
    dates=f["daily"]["time"]; tmax=f["daily"]["temperature_2m_max"]; tmin=f["daily"]["temperature_2m_min"]; pp=f["daily"]["precipitation_probability_max"]; codes=f["daily"]["weathercode"]
    out_paths=[]
    for i in range(days):
        name = f"forecast_{city}_{i+1}.txt".replace(" ","_")
        p = DESK / name
        txt = f"{city}  Day {i+1}\nDate: {dates[i]}\nMax: {round(tmax[i])}C  Min: {round(tmin[i])}C  Precip: {pp[i]}%  Code:{codes[i]}\nSource: Open-Meteo"
        p.write_text(txt, encoding="utf-8")
        out_paths.append(str(p))
    return out_paths

if __name__ == '__main__':
    # small self-test for OpenHands diagnostics
    res = {
        "monitors": count_monitors(),
        "windows": count_windows(),
        "screenshot": screenshot(),
        "titles": list_window_titles()[:10]
    }
    (ROOT/'reports'/'TOOLS_DIAG.json').write_text(json.dumps(res, indent=2), encoding='utf-8')
    print(json.dumps({"ok":True}))
'@
Set-Content -Encoding Ascii -LiteralPath .\dev\local_tools.py -Value $lt

# --- Brain Chat shell: intents + commands + planner kick (GPT-5 locked) ---
$bs = @'
import os, sys, re, json, time, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT/'reports'/'chat'/'exact_tail.jsonl'
TAIL.parent.mkdir(parents=True, exist_ok=True)
if not TAIL.exists(): TAIL.write_text("", encoding='ascii', errors='ignore')

def asc(s): return (s or "").encode("ascii","ignore").decode("ascii")

def append(role, text):
    line={"ts":time.strftime("%Y-%m-%d %H:%M:%S"),"role":role,"text":asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f: f.write(json.dumps(line, ensure_ascii=True)+"\n")

def read_model_lock():
    cfg=(ROOT/'configs'/'model.yaml').read_text(errors='ignore') if (ROOT/'configs'/'model.yaml').exists() else "default: gpt-5\nlock: true\n"
    m=re.search(r'(?im)^\s*default\s*:\s*([^\r\n#]+)', cfg); default=(m.group(1).strip() if m else 'gpt-5')
    lock=bool(re.search(r'(?im)^\s*lock\s*:\s*(true|True|1)', cfg))
    return default, lock

def run(cmd): 
    try: return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
    except Exception: return None

def try_planner(q):
    py=str(ROOT/'.venv/ Scripts/python.exe'); py=py.replace(' ','')
    if not pathlib.Path(py).exists(): py='python'
    run([py, 'dev/eco_cli.py','ask',q]); run([py,'dev/core02_planner.py','apply'])

def llm_reply(q, model):
    key_path=ROOT/'api_key.txt'
    key=key_path.read_text().strip() if key_path.exists() else os.environ.get('OPENAI_API_KEY','')
    if not key: return '(no assistant reply yet - set OPENAI_API_KEY or api_key.txt)'
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        sys_prompt='You are the Ecosystem Brain on Windows. Be concise, answer directly, and give executable steps when a PC action is requested.'
        r=client.chat.completions.create(model=model, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":q}])
        return asc((r.choices[0].message.content or '').strip())
    except Exception as e:
        return asc(f'(model error: {e})')

def poll_tail(timeout=15, min_wait=1.0):
    t0=time.time(); time.sleep(min_wait); end=t0+timeout
    while time.time()<end:
        try:
            lines=TAIL.read_text(encoding='ascii',errors='ignore').splitlines()
            for ln in reversed(lines):
                try:
                    o=json.loads(ln)
                    if o.get('role') in ('assistant','brain') and o.get('text') and not str(o.get('text','')).startswith('echo:'):
                        return o['text']
                except: pass
        except: pass
        time.sleep(0.4)
    return None

# local tools wiring
sys.path.insert(0, str(ROOT/'dev'))
import local_tools as LT  # type: ignore

def try_local(q:str)->str|None:
    s=q.lower().strip()
    # commands
    if s.startswith('/status'): return f'OK (tail={TAIL})'
    if s.startswith('/monitors'): return f'Monitors detected: {LT.count_monitors()}'
    if s.startswith('/windows'): return f'Windows open: {LT.count_windows()}'
    if s.startswith('/titles'):  return 'Titles: ' + '; '.join(LT.list_window_titles()[:20]) or 'Titles: (none)'
    m=re.match(r'^/screenshot(?:\s+(\S+))?$', s)
    if m: return 'Screenshot: ' + LT.screenshot(m.group(1) or None)

    # intents
    m=re.search(r'forecast\s+(?P<days>\d+)\s*day[s]?\s+for\s+(?P<city>.+)', s)
    if m:
        city=m.group('city').strip()
        days=int(m.group('days'))
        try:
            paths=LT.forecast_to_desktop(city, days)
            return 'Forecast files: ' + ', '.join(paths)
        except Exception as e:
            return f'(forecast error: {e})'

    m=re.match(r'open\s+notepad$', s) or re.match(r'open\s+notepad\s+and\s+type\s+(.+)', s)
    if m:
        LT.open_app('notepad.exe'); time.sleep(0.7)
        if 'type' in s:
            txt=s.split('type',1)[1].strip()
            LT.type_text(txt)
        return 'Notepad opened'

    m=re.match(r'/click\s+(\d+)\s+(\d+)$', s)
    if m:
        x,y=int(m.group(1)),int(m.group(2)); LT.mouse_move(x,y); LT.click(); return f'Clicked {x},{y}'

    m=re.match(r'/keys\s+(.+)$', s)
    if m: LT.keys(m.group(1)); return '(keys sent)'

    return None

def main():
    model, locked = read_model_lock()
    print('Brain chat ready. Type "exit" to quit.')
    print(f'(model={model}{" [LOCKED]" if locked else ""})')
    while True:
        try: q=input('You> ').strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=='exit': break
        if q.lower().startswith('/model'):
            print('(model is LOCKED to gpt-5)' if locked else f'(current model {model})')
            continue
        # local fast path
        local = try_local(q)
        append('user', q)
        try_planner(q)
        if local:
            append('assistant', local); print(local)
        else:
            ans = llm_reply(q, model); append('assistant', ans); print(ans)
        extra = poll_tail()
        if extra: print(f'[ecosystem] {extra}')
    print('Bye.')
if __name__=='__main__': main()
'@
Set-Content -Encoding Ascii -LiteralPath .\dev\brain_chat_shell.py -Value $bs

# --- runner: stop -> start bg -> launch shell (danger mode on) ---
$run = @'
param()
$ErrorActionPreference='Stop'
$ROOT = $PSScriptRoot; if (-not $ROOT) { $ROOT = (Convert-Path '.') }
Set-Location $ROOT
$env:MODEL_NAME='gpt-5'
$env:AGENT_DANGER_MODE='1'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
$py = Join-Path $ROOT '.venv\Scripts\python.exe'; if(-not (Test-Path $py)){ $py='python' }
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
'@
Set-Content -Encoding Ascii -LiteralPath .\dev\run_chat_full.ps1 -Value $run

# --- quick autonomous smoke (open notepad, type, save, screenshot) ---
$smk = @'
import time, os, pathlib, json
from dev import local_tools as LT
desk = pathlib.Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
ok_path = desk/"eco_ok.txt"
LT.open_app("notepad.exe"); time.sleep(0.8)
LT.type_text("Ecosystem OK"); time.sleep(0.2)
LT.keys("ctrl+s"); time.sleep(0.5)
LT.type_text(str(ok_path)); time.sleep(0.2)
LT.keys("enter"); time.sleep(0.6)
shot = LT.screenshot()
out = {"ok_file": str(ok_path), "screenshot": shot, "monitors": LT.count_monitors(), "windows": LT.count_windows()}
(pathlib.Path("reports")/"AUTO_ASSERT.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({"ok":True}))
'@
Set-Content -Encoding Ascii -LiteralPath .\dev\_auto_assert.py -Value $smk

# --- (re)start background and run asserts ---
powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

& $py -m dev.local_tools > $null 2>$null
& $py .\dev\_auto_assert.py > $null 2>$null

Write-Host 'ULTRA-AUTO READY'
Write-Host ('Assert: ' + (Get-Content .\reports\AUTO_ASSERT.json -Raw))
