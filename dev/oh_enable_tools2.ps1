param()
$ErrorActionPreference='Stop'
$ROOT = 'C:\bots\ecosys'
Set-Location $ROOT

function Write-Ascii($Path,$Text){ $dir=Split-Path -Parent $Path; if($dir){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }; [IO.File]::WriteAllText($Path,$Text,[Text.Encoding]::ASCII) }

# --- Ensure venv + deps ---
$py='..\..\bots\ecosys\.venv\Scripts\python.exe'
$py='..\..\bots\ecosys\.venv\Scripts\python.exe'
$py='.\.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv .venv } else { python -m venv .venv }
  $py='..\..\bots\ecosys\.venv\Scripts\python.exe'
  $py='.\.venv\Scripts\python.exe'
}
& $py -m pip -q install --upgrade pip
& $py -m pip -q install pywin32 mss pillow screeninfo keyboard requests

# --- Ensure dev package marker ---
if(!(Test-Path '.\dev\__init__.py')){ Write-Ascii '.\dev\__init__.py' '' }

# --- Write dev\local_tools.py (windows/monitors/screenshot/forecast) ---
$newTools = @'
import os, json, time, pathlib, ctypes
from datetime import datetime
# Windows handles
try:
    import win32gui, win32con
    HAVE_WIN32=True
except Exception:
    HAVE_WIN32=False
# Screenshots
try:
    import mss, mss.tools
    HAVE_MSS=True
except Exception:
    HAVE_MSS=False
# PIL optional for later compositing
try:
    from PIL import Image
    HAVE_PIL=True
except Exception:
    HAVE_PIL=False
# screen info
try:
    from screeninfo import get_monitors
    HAVE_SCREENINFO=True
except Exception:
    HAVE_SCREENINFO=False

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT/'reports'
SCREENS = REPORTS/'screens'
DESKTOP = pathlib.Path(os.path.join(os.environ.get('USERPROFILE',''), 'Desktop'))

def _ensure_dirs():
    REPORTS.mkdir(parents=True, exist_ok=True)
    SCREENS.mkdir(parents=True, exist_ok=True)

def count_monitors():
    if HAVE_SCREENINFO:
        try:
            return len(get_monitors()) or 0
        except Exception:
            pass
    # Fallback via win32 EnumDisplayMonitors
    if HAVE_WIN32 and hasattr(ctypes.windll, 'user32'):
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            monitors = ctypes.c_int()
            def _cb(hMon, hdc, lprc, data):
                monitors.value += 1
                return 1
            MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.c_long*4), ctypes.c_double)
            cb = MONITORENUMPROC(_cb)
            user32.EnumDisplayMonitors(0, 0, cb, 0)
            return int(monitors.value)
        except Exception:
            pass
    return 0

def count_windows():
    if not HAVE_WIN32:
        return 0
    titles=[]
    def enum_handler(hWnd, param):
        if win32gui.IsWindowVisible(hWnd):
            title = win32gui.GetWindowText(hWnd)
            if title and title.strip():
                titles.append(title)
    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        return 0
    return len(titles)

def screenshot():
    _ensure_dirs()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = SCREENS/f'screen_{ts}.png'
    if not HAVE_MSS:
        return None
    try:
        with mss.mss() as sct:
            shot = sct.shot(mon=-1, output=str(out))  # primary
        return str(out)
    except Exception:
        return None

def forecast_budapest_to_desktop(days=3):
    # No geocoding: fixed Budapest approx lat/lon
    lat, lon = 47.4979, 19.0402
    import urllib.request, json as _json
    url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days={max(1,min(days,5))}&timezone=auto'
    data=None
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = _json.loads(r.read().decode('utf-8','ignore'))
    except Exception:
        return {'ok':False,'err':'fetch_failed'}

    def cond(code:int):
        m={0:'Clear',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Depositing rime fog',
           51:'Light drizzle',53:'Moderate drizzle',55:'Dense drizzle',61:'Slight rain',63:'Moderate rain',65:'Heavy rain',
           80:'Slight rain showers',81:'Moderate rain showers',82:'Violent rain showers',95:'Thunderstorm',96:'T-storm slight hail',99:'T-storm heavy hail'}
        return m.get(int(code),'Unknown')

    times = data.get('daily',{}).get('time',[]) or []
    tmax  = data.get('daily',{}).get('temperature_2m_max',[]) or []
    tmin  = data.get('daily',{}).get('temperature_2m_min',[]) or []
    pprob = data.get('daily',{}).get('precipitation_probability_max',[]) or []
    code  = data.get('daily',{}).get('weathercode',[]) or []

    made=[]
    for i,day in enumerate(times[:days]):
        line = f"Budapest {day}  Max:{round(tmax[i]) if i<len(tmax) else '?'}C  Min:{round(tmin[i]) if i<len(tmin) else '?'}C  Precip:{(str(pprob[i])+'%') if i<len(pprob) and pprob[i] is not None else 'n/a'}  Cond:{cond(code[i] if i<len(code) else 0)}"
        path = DESKTOP/f'fore{i+1}.txt'
        with open(path,'w',encoding='utf-8',errors='ignore') as f:
            f.write('3-Day Forecast (Budapest)\n'+line+'\n')
        made.append(str(path))
    return {'ok':True,'files':made}
'@
Write-Ascii 'dev\local_tools.py' $newTools

# --- Overwrite dev\brain_chat_shell.py (tools-first, no echo-dump) ---
$newShell = @'
import os, sys, json, time, subprocess, pathlib
from dev import local_tools as tools

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / 'reports' / 'chat' / 'exact_tail.jsonl'
TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)

def asc(s): return (s or '').encode('ascii','ignore').decode('ascii')
def log(role,text):
    line={'ts':time.strftime('%Y-%m-%d %H:%M:%S'),'role':role,'text':asc(text)}
    with open(TAIL,'a',encoding='ascii',errors='ignore') as f: f.write(json.dumps(line,ensure_ascii=True)+'\n')

def openai_answer(q):
    key_path=ROOT/'api_key.txt'
    key= key_path.read_text().strip() if key_path.exists() else os.environ.get('OPENAI_API_KEY','')
    if not key: return None
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        sys_prompt='You are the Ecosystem Brain on Windows. Be concise and do the task directly.'
        r=client.chat.completions.create(model=os.environ.get('MODEL_NAME','gpt-5'),
            messages=[{'role':'system','content':sys_prompt},{'role':'user','content':q}])
        return asc((r.choices[0].message.content or '').strip())
    except Exception as e:
        return asc(f'(model error: {e})')

def planner_kick(q):
    py = str(ROOT/'.venv'/'Scripts'/'python.exe');  py = py if pathlib.Path(py).exists() else 'python'
    try: subprocess.run([py,'dev/eco_cli.py','ask',q], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass
    try: subprocess.run([py,'dev/core02_planner.py','apply'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def handle_tools(q:str):
    s=q.lower()
    if '/status' in s:
        info={'monitors':tools.count_monitors(),'windows':tools.count_windows()}
        return f"status: monitors={info['monitors']} windows={info['windows']}"
    if '/monitors' in s or 'how many monitors' in s:
        return f"monitors: {tools.count_monitors()}"
    if '/windows' in s or 'how many windows' in s:
        return f"windows: {tools.count_windows()}"
    if '/screenshot' in s or 'screenshot' in s:
        p=tools.screenshot()
        return f'screenshot: {p if p else "failed"}'
    if 'forecast' in s and 'budapest' in s:
        out=tools.forecast_budapest_to_desktop(3)
        if out and out.get('ok'):
            return 'forecast: wrote ' + ', '.join(out['files'])
        return 'forecast: failed'
    return None

def poll_ecosystem(last, timeout=12):
    t0=time.time()
    while time.time()-t0<timeout:
        try:
            lines=open(TAIL,'r',encoding='ascii',errors='ignore').read().splitlines()
            for ln in reversed(lines):
                try:
                    o=json.loads(ln)
                    txt=o.get('text') or ''
                    if o.get('role') in ('assistant','brain') and txt and txt!=last and not txt.startswith('echo:'):
                        # filter common noise
                        if txt.strip().lower().startswith('hi! how can i help you today?'): continue
                        return txt
                except: pass
        except: pass
        time.sleep(0.6)
    return None

def main():
    print('Brain chat ready. Type "exit" to quit.')
    print('(model='+os.environ.get('MODEL_NAME','gpt-5')+')')
    while True:
        try: q=input('You> ').strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=='exit': break

        log('user', q)
        # 1) tools first
        t = handle_tools(q)
        if t:
            log('assistant', t); print(t)
            planner_kick(q)  # still kick in background
            extra=poll_ecosystem(t, timeout=8)
            if extra: print('[ecosystem] '+extra)
            continue

        # 2) immediate LLM answer
        ans = openai_answer(q) or '(no answer)'
        log('assistant', ans); print(ans)

        # 3) background planner
        planner_kick(q)
        extra=poll_ecosystem(ans, timeout=8)
        if extra: print('[ecosystem] '+extra)

    print('Bye.')
if __name__=='__main__': main()
'@
Write-Ascii 'dev\brain_chat_shell.py' $newShell

# --- Fix launcher to always find Python and deps ---
$runner = @'
param()
$ErrorActionPreference = 'Stop'
$ROOT = $PSScriptRoot; if(-not $ROOT){ $ROOT = 'C:\bots\ecosys' }
Set-Location $ROOT
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if(-not (Test-Path $py)){ $py = 'python' }
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
'@
Write-Ascii 'dev\run_chat_full.ps1' $runner

# --- Route Comms -> Brain (echo off), apply plan, restart background ---
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}
& $py dev\chatops_cli.py 'Switch Comms to Brain (GPT) mode, disable echo, route bus ''comms/in'' to Brain, write replies to reports\chat\exact_tail.jsonl' | Out-Null
& $py dev\core02_planner.py apply | Out-Null
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

# --- Non-interactive SELF-TESTS (no user typing) ---
Write-Host '--- SELF-TESTS ---'
$st = @'
import json
from dev import local_tools as t
print(json.dumps({'monitors': t.count_monitors()}))
print(json.dumps({'windows': t.count_windows()}))
print(json.dumps({'screenshot': bool(t.screenshot())}))
print(json.dumps(t.forecast_budapest_to_desktop(3)))
'@
Write-Ascii 'dev\tools_selftest.py' $st
$smoke = & $py -m dev.tools_selftest
Write-Ascii 'reports\TOOLS_SMOKE.txt' $smoke

Write-Host $smoke
Write-Host '--- READY ---'
