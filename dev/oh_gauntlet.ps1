param()
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# Root & required dirs
$ROOT = 'C:\bots\ecosys'
$DEV  = Join-Path $ROOT 'dev'
$CFG  = Join-Path $ROOT 'config'
$RPTS = Join-Path $ROOT 'reports'
$CHAT = Join-Path $RPTS 'chat'
$SCRN = Join-Path $RPTS 'screens'
$LOGS = Join-Path $ROOT 'logs'
$dirs = @($ROOT,$DEV,$CFG,$RPTS,$CHAT,$SCRN,$LOGS)
foreach($d in $dirs){ if(-not (Test-Path $d)){ New-Item -ItemType Directory -Force -Path $d | Out-Null } }

# Tail file
$tail = Join-Path $CHAT 'exact_tail.jsonl'
if(-not (Test-Path $tail)){ '' | Set-Content -Encoding Ascii -LiteralPath $tail }

# Configs
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'model.yaml') @'
default: gpt-5
lock: true
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'comms.yaml') @'
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
'@

# dev package
if(-not (Test-Path (Join-Path $DEV '__init__.py'))){ '' | Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '__init__.py') }

# Pick python
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if(-not (Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $ROOT '.venv') } else { python -m venv (Join-Path $ROOT '.venv') }
  $py = Join-Path $ROOT '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --upgrade --quiet `
  'openai>=1,<2' psutil pywin32 mss pillow screeninfo keyboard requests pyautogui | Out-Null

# Write gauntlet python
$gauntlet = @'
import os, sys, json, time, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RPTS = ROOT / "reports"
CHAT = RPTS / "chat"
SCRN = RPTS / "screens"
DESK = Path(os.path.expanduser("~")) / "Desktop"
SCRN.mkdir(parents=True, exist_ok=True)
CHAT.mkdir(parents=True, exist_ok=True)

res = {"ok": True, "errors": [], "artifacts": {}}

def err(msg):
    res["ok"] = False
    res["errors"].append(str(msg))

# monitors

def count_monitors():
    try:
        from screeninfo import get_monitors
        return {"monitors": len(get_monitors())}
    except Exception as e:
        return {"monitors": 0}

# windows

def count_windows():
    try:
        import win32gui
        def is_visible_top(h):
            try:
                return win32gui.IsWindowVisible(h) and win32gui.GetWindowTextLength(h) > 0
            except: return False
        n=0
        def enum_handler(h,l):
            nonlocal n
            if is_visible_top(h): n+=1
            return True
        win32gui.EnumWindows(enum_handler, None)
        return {"windows": n}
    except Exception:
        return {"windows": 0}

# screenshot

def screenshot(prefix="hb"):
    try:
        import mss, time
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = SCRN / f"{prefix}_{ts}.png"
        with mss.mss() as s:
            s.shot(output=str(path))
        return str(path)
    except Exception as e:
        err("screenshot:"+str(e))
        return None

# desktop write
try:
    df = DESK / "hb_check.txt"
    df.write_text("ok", encoding="utf-8")
    res["artifacts"]["desktop_write"] = str(df)
except Exception as e:
    err("desktop_write:"+str(e))

# openai connectivity (optional)
key = os.environ.get("OPENAI_API_KEY","")
if not key:
    kf = ROOT / "api_key.txt"
    if kf.exists():
        key = kf.read_text().strip()

if key:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        r = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role":"user","content":"ping"}],
            max_completion_tokens=4,
        )
        res["artifacts"]["openai_ok"] = True
        res["artifacts"]["model"] = "gpt-5"
    except Exception as e:
        res["artifacts"]["openai_ok"] = False
        err("openai:"+str(e))
else:
    res["artifacts"]["openai_ok"] = False

# run
res["artifacts"]["monitors"] = count_monitors()
res["artifacts"]["windows"]  = count_windows()
res["artifacts"]["screenshot"] = screenshot("gauntlet")

# save
out = RPTS / "HARD_GAUNTLET_RESULT.json"
with out.open("w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(json.dumps(res, ensure_ascii=False))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'gauntlet.py') -Value $gauntlet

# Clean stop any background
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}

# Bring background up briefly to verify planner + assistant tail
$tailOk = $false
try {
  powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -HeartbeatSec 2 -HealthSec 2 | Out-Null
  & $py dev\core02_planner.py apply | Out-Null
  & $py dev\eco_cli.py ask ping       | Out-Null

  $deadline = (Get-Date).AddSeconds(60)
  while((Get-Date) -lt $deadline -and -not $tailOk){
    Start-Sleep -Seconds 3
    $tailText = try { Get-Content -LiteralPath $tail -Tail 200 -ErrorAction Stop | Out-String } catch { '' }
    if($tailText -and ($tailText -match '\[ecosystem\]' -or $tailText -match '"assistant"' -or $tailText -match 'Bridges ready')){
      if($tailText -notmatch '^echo:'){
        $tailOk = $true
      }
    }
  }
} catch {}
# Clean stop background again
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}

# Run gauntlet python
$ga = & $py -m dev.gauntlet
$gaJson = $null
try { $gaJson = $ga | ConvertFrom-Json } catch { }

# Build summary
$overall = $true
if(-not $tailOk){ $overall = $false }
if($gaJson -ne $null -and -not $gaJson.ok){ $overall = $false }

$sumPath = Join-Path $RPTS 'HARD_GAUNTLET_SUMMARY.txt'
$lines = @()
$lines += ('[{0}] HARD GAUNTLET' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$lines += ('tail_ok={0}' -f $tailOk)
if($gaJson -eq $null){
  $lines += 'gauntlet_json=parse_error'
  $overall = $false
}else{
  $lines += ('tools_ok={0}' -f $gaJson.ok)
  $lines += ('openai_ok={0}' -f $gaJson.artifacts.openai_ok)
  $lines += ('monitors={0}' -f $gaJson.artifacts.monitors.monitors)
  $lines += ('windows={0}'  -f $gaJson.artifacts.windows.windows)
  $lines += ('screenshot={0}' -f $gaJson.artifacts.screenshot)
}
$lines += ('overall_ok={0}' -f $overall)
$lines | Set-Content -Encoding Ascii -LiteralPath $sumPath

Write-Host ('WROTE: ' + $sumPath)
if($overall){ exit 0 } else { exit 1 }
