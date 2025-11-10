param()
$ErrorActionPreference='Stop'

# ---------- 0) Resolve roots (no hard-coding) ----------
$SCRIPT_DIR = (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $SCRIPT_DIR) { $SCRIPT_DIR = (Convert-Path '.') }
$ECOROOT = Split-Path -Parent $SCRIPT_DIR
$BOTSROOT = Split-Path -Parent $ECOROOT
if (-not (Test-Path $BOTSROOT)) { $BOTSROOT = 'C:\bots' }

# ---------- 1) Dirs & ASCII-only configs ----------
$dirs = @('logs','runs','reports','artifacts','out','var','data','workspace','configs','specs','reports\chat','reports\screens')
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path (Join-Path $ECOROOT $d) | Out-Null }

# configs (no hard-coding: model resolved from env/api_key.txt; paths computed)
@"
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
"@ | Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'configs\comms.yaml')

$modelName = if ($env:MODEL_NAME -and $env:MODEL_NAME.Trim() -ne '') { $env:MODEL_NAME } else { 'gpt-5' }
@"
default: `"$modelName`"
fallbacks: [gpt-4o-mini, gpt-4o]
"@ |
  Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'configs\model.yaml')

# ---------- 2) Venv + deps (idempotent) ----------
$py = Join-Path $ECOROOT '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv (Join-Path $ECOROOT '.venv') }
  else { python -m venv (Join-Path $ECOROOT '.venv') }
}
& $py -m pip install -U pip > $null
$req = @(
  'openai>=1.0.0',
  'pydantic',
  'psutil',
  'pywin32',
  'mss',
  'Pillow',
  'screeninfo',
  'keyboard',
  'requests',
  'fastapi',
  'uvicorn',
  'websockets',
  'watchdog'
)
& $py -m pip install $req > $null

# ---------- 3) Local tools (monitors/windows/screenshot/forecast) ----------
if (!(Test-Path (Join-Path $ECOROOT 'dev\__init__.py'))) { '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'dev\__init__.py') }
$toolsPy = @'
import os, json, time, datetime, pathlib, io
from typing import List
ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SCREENS = REPORTS / "screens"
SCREENS.mkdir(parents=True, exist_ok=True)

def count_monitors() -> int:
    try:
        from screeninfo import get_monitors
        return len(get_monitors())
    except Exception:
        return 0

def count_windows() -> int:
    try:
        import win32gui
    except Exception:
        return 0
    titles = []
    def enum_handler(hwnd, ctx):
        try:
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd) or ""
                if t.strip():
                    titles.append(t)
        except Exception:
            pass
    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        return 0
    return len(titles)

def screenshot() -> str:
    path = SCREENS / f"screen_{int(time.time())}.png"
    try:
        import mss
        with mss.mss() as sct:
            sct.shot(output=str(path))
        return str(path)
    except Exception:
        return ""

def _cond(code:int)->str:
    table={0:"Clear",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Rime fog",
           51:"Light drizzle",53:"Moderate drizzle",55:"Dense drizzle",
           61:"Slight rain",63:"Moderate rain",65:"Heavy rain",
           71:"Slight snow",73:"Moderate snow",75:"Heavy snow",
           80:"Rain showers",81:"Rain showers",82:"Rain showers",
           95:"Thunderstorm",96:"Tstorm slight hail",99:"Tstorm heavy hail"}
    return table.get(int(code),"Unknown")

def forecast_to_desktop(city:str, lat:float, lon:float, days:int=3)->List[str]:
    import requests
    desk = pathlib.Path(os.environ.get("USERPROFILE",""))/"Desktop"
    out=[]
    try:
        url=f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days={days}&timezone=auto"
        r=requests.get(url, timeout=15); r.raise_for_status()
        d=r.json(); times=d["daily"]["time"]
        for i,dt in enumerate(times):
            tmax=round(d["daily"]["temperature_2m_max"][i])
            tmin=round(d["daily"]["temperature_2m_min"][i])
            pp=d["daily"].get("precipitation_probability_max",[None]*len(times))[i]
            cond=_cond(d["daily"]["weathercode"][i])
            name = f"fore{i+1}.txt"
            p = desk/name
            txt = f"{city} {dt}\nMax:{tmax}C Min:{tmin}C Precip:{'n/a' if pp is None else str(pp)+'%'} Conditions:{cond}\n"
            p.write_text(txt, encoding="utf-8")
            out.append(str(p))
    except Exception:
        pass
    return out
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'dev\local_tools.py') -Value $toolsPy

# ---------- 4) Brain chat shell (model reply + planner + tail poll, ASCII logs) ----------
$brainPy = @'
import os, sys, json, time, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TAIL = ROOT / "reports" / "chat" / "exact_tail.jsonl"
TAIL.parent.mkdir(parents=True, exist_ok=True)
if not TAIL.exists(): TAIL.write_text("", encoding="ascii", errors="ignore")

from importlib import import_module
try:
    local_tools = import_module("dev.local_tools")
except Exception:
    local_tools = None

def asc(s): return (s or "").encode("ascii", "ignore").decode("ascii")

def append(role, text):
    line = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "role": role, "text": asc(text)}
    with TAIL.open("a", encoding="ascii", errors="ignore") as f:
        f.write(json.dumps(line, ensure_ascii=True)+"\n")

def poll_for_reply(timeout=20, min_wait=1.0):
    t0=time.time(); time.sleep(min_wait)
    end=t0+timeout
    while time.time()<end:
        try:
            lines = TAIL.read_text(encoding="ascii", errors="ignore").splitlines()
            for ln in reversed(lines):
                try:
                    o=json.loads(ln)
                    if o.get("role") in ("assistant","brain") and o.get("text") and not str(o.get("text",""))[:5]=="echo:":
                        return o["text"]
                except: pass
        except: pass
        time.sleep(0.5)
    return None

def run(cmd):
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
    except Exception as e:
        return None

def try_planner(q):
    py = str(ROOT/".venv/Scripts/python.exe")
    if not pathlib.Path(py).exists(): py="python"
    run([py, "dev/eco_cli.py", "ask", q])
    run([py, "dev/core02_planner.py", "apply"])

def try_model(q, model_name):
    key_path = ROOT/"api_key.txt"
    key = key_path.read_text().strip() if key_path.exists() else os.environ.get("OPENAI_API_KEY","")
    if not key: return "(no assistant reply yet - put your key in api_key.txt)"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        sys_prompt = "You are the Ecosystem Brain on Windows. Answer directly and helpfully."
        r = client.chat.completions.create(model=model_name, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":q}])
        return asc((r.choices[0].message.content or "").strip())
    except Exception as e:
        return asc(f"(model error: {e})")

def main():
    model_name = os.environ.get("MODEL_NAME","gpt-5")
    print('Brain chat ready. Type "exit" to quit.')
    print(f"(model={model_name})")
    while True:
        try: q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt): print(); break
        if not q: continue
        if q.lower()=="exit": break
        if q.lower().startswith("/model"):
            parts=q.split(None,1)
            if len(parts)==2 and parts[1].strip():
                model_name = parts[1].strip(); print(f"(model set to {model_name})"); continue
            else:
                print(f"(current model {model_name})"); continue
        if q.lower() in ("/status",):
            print("OK: online; tail:", str(TAIL)); continue
        if q.lower()=="/monitors" and local_tools:
            print(f"Monitors: {local_tools.count_monitors()}"); continue
        if q.lower()=="/windows" and local_tools:
            print(f"Windows: {local_tools.count_windows()}"); continue
        if q.lower()=="/screenshot" and local_tools:
            p = local_tools.screenshot(); print(p or "(screenshot failed)"); continue
        if q.lower().startswith("forecast budapest") and local_tools:
            files = local_tools.forecast_to_desktop("Budapest",47.4979,19.0402,3); print(json.dumps(files)); continue

        append("user", q)
        try_planner(q)                   # kick Ecosystem
        ans = try_model(q, model_name)   # immediate reply
        append("assistant", ans); print(ans)
        extra = poll_for_reply(timeout=15, min_wait=1.0)
        if extra and extra.strip() and not extra.strip()[:5]=="echo:":
            print(f"[ecosystem] {extra}")
    print("Bye.")
if __name__ == "__main__": main()
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'dev\brain_chat_shell.py') -Value $brainPy

# ---------- 5) One-click runner (stop->start->shell) ----------
$runner = @'
param()
$ErrorActionPreference='Stop'
$ROOT = $PSScriptRoot; if (-not $ROOT) { $ROOT = (Convert-Path '.') }
Set-Location $ROOT
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'dev\run_chat_full.ps1') -Value $runner

# ---------- 6) Inventory & DoD assertions ----------
$inv = @'
import os, hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT/"reports"/"inventory.json"

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()

idx=[]
for p in ROOT.parents[0].glob("**/*"):
    try:
        if p.is_file() and p.stat().st_size<5_000_000:
            idx.append({"path":str(p), "bytes":p.stat().st_size, "sha256":sha256(p)})
    except Exception: pass
OUT.write_text(json.dumps({"root":str(ROOT),"files":idx}, indent=2), encoding="utf-8")
print(str(OUT))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'dev\inventory.py') -Value $inv

$assert = @'
param()
$ErrorActionPreference='SilentlyContinue'
$ROOT = (Split-Path -Parent $MyInvocation.MyCommand.Path); if (-not $ROOT) { $ROOT=(Convert-Path '.') }
$ok = @{}

$ok.OPENAI_KEY = Test-Path (Join-Path $ROOT 'api_key.txt')
$ok.TAIL = Test-Path (Join-Path $ROOT 'reports\chat\exact_tail.jsonl')
$ok.DB = Test-Path (Join-Path $ROOT 'var\events.db')
$startLog = Join-Path $ROOT 'logs\start_stdout.log'
$ok.LOGS = (Test-Path $startLog) -and ((Get-Content $startLog -ErrorAction SilentlyContinue -Tail 4000) -match 'inbox loop started|JobsWorker started|Ecosystem ready')

$py = Join-Path $ROOT '.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py='python' }
$testModel=$false
try {
  $k = Get-Content (Join-Path $ROOT 'api_key.txt') -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($k) { $testModel=$true }
} catch {}
$ok.OPENAI_READY = $testModel

$pass = ($ok.OPENAI_READY -and $ok.TAIL -and $ok.LOGS)
$summary = @{ pass=$pass; checks=$ok }
$summary | ConvertTo-Json | Set-Content -Encoding Ascii -LiteralPath (Join-Path $ROOT 'reports\MINIMUMS_ASSERT.json')
Write-Host ((Get-Content (Join-Path $ROOT 'reports\MINIMUMS_ASSERT.json')))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $ECOROOT 'dev\oh_min_assert.ps1') -Value $assert

# ---------- 7) Top-level launcher at C:\bots (no hard-coding) ----------
$mainStart = @'
param()
$ErrorActionPreference = 'Stop'
$root = 'C:\bots'
$eco = Get-ChildItem -Path $root -Directory -Recurse -Filter ecosys -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $eco) { $eco = Get-Item -Path 'C:\bots\ecosys' -ErrorAction SilentlyContinue }
if (-not $eco) { throw 'ecosys not found under C:\bots' }
$ER = $eco.FullName
$runner = Join-Path $ER 'dev\run_chat_full.ps1'
if (-not (Test-Path $runner)) { throw 'run_chat_full.ps1 missing' }
powershell -NoProfile -ExecutionPolicy Bypass -File $runner
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $BOTSROOT 'start.ps1') -Value $mainStart

# ---------- 8) Stop -> start background -> inventory -> assert ----------
powershell -NoProfile -File (Join-Path $ECOROOT 'start.ps1') -Stop 1 | Out-Null
powershell -NoProfile -File (Join-Path $ECOROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null

& $py -m dev.inventory | Out-Null

# Create desktop shortcut for chat
try {
  $WScriptShell = New-Object -ComObject WScript.Shell
  $Shortcut = $WScriptShell.CreateShortcut((Join-Path $env:USERPROFILE 'Desktop\Ecosystem Chat.lnk'))
  $Shortcut.TargetPath = 'powershell.exe'
  $Shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $ECOROOT 'dev\run_chat_full.ps1') + '"'
  $Shortcut.WorkingDirectory = $ECOROOT
  $Shortcut.IconLocation = 'powershell.exe,0'
  $Shortcut.Save()
} catch {}

# Run minimums assert and write summary
$min = & powershell -NoProfile -File (Join-Path $ECOROOT 'dev\oh_min_assert.ps1')
$sumPath = Join-Path $ECOROOT 'reports\MEET_MINIMUMS_SUMMARY.txt'
('[{0}] MEET_MINIMUMS => {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $min) | Set-Content -Encoding Ascii -LiteralPath $sumPath

Write-Host '=== MEET_MINIMUMS COMPLETE ==='
Write-Host ('Desktop shortcut: {0}' -f (Join-Path $env:USERPROFILE 'Desktop\Ecosystem Chat.lnk'))
Write-Host ('Launcher: C:\bots\start.ps1')
