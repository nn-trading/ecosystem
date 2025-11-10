param([switch]$StopAfter=$false)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'

# Paths
$ROOT='C:\bots\ecosys'; $DEV=Join-Path $ROOT 'dev'; $CFG=Join-Path $ROOT 'config'
$RPTS=Join-Path $ROOT 'reports'; $CHAT=Join-Path $RPTS 'chat'; $SCRN=Join-Path $RPTS 'screens'; $LOGS=Join-Path $ROOT 'logs'; $RUNS=Join-Path $ROOT 'runs'
$dirs=@($ROOT,$DEV,$CFG,$RPTS,$CHAT,$SCRN,$LOGS,$RUNS); foreach($d in $dirs){ if(!(Test-Path $d)){ New-Item -ItemType Directory -Force -Path $d|Out-Null } }
if(!(Test-Path (Join-Path $DEV '__init__.py'))){ ''|Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '__init__.py') }
$tail=Join-Path $CHAT 'exact_tail.jsonl'; if(!(Test-Path $tail)){ ''|Set-Content -Encoding Ascii -LiteralPath $tail }

# Enforce configs (correct: config\)
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'model.yaml') @'
default: gpt-5
lock: true
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'comms.yaml') @'
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
'@

# Python + deps
$py=Join-Path $ROOT '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $ROOT '.venv') } else { python -m venv (Join-Path $ROOT '.venv') }
  $py=Join-Path $ROOT '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --upgrade --quiet 'openai>=1,<2' psutil pywin32 mss pillow screeninfo keyboard requests pyautogui | Out-Null

# Gauntlet (tools + OpenAI)
$ga=@'
import os, json, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RPTS=ROOT/"reports"; CHAT=RPTS/"chat"; SCRN=RPTS/"screens"; DESK=Path(os.path.expanduser("~"))/"Desktop"
SCRN.mkdir(parents=True, exist_ok=True); CHAT.mkdir(parents=True, exist_ok=True)
res={"ok":True,"errors":[],"artifacts":{}}
def err(m): res.setdefault("errors",[]).append(str(m)); res["ok"]=False
def count_monitors():
  try:
    from screeninfo import get_monitors
    return {"monitors": len(get_monitors())}
  except Exception: return {"monitors": 0}
def count_windows():
  try:
    import win32gui
    def ok(h):
      try: return win32gui.IsWindowVisible(h) and win32gui.GetWindowTextLength(h)>0
      except: return False
    n=0
    def enum(h,l):
      nonlocal n
      if ok(h): n+=1
      return True
    win32gui.EnumWindows(enum,None)
    return {"windows": n}
  except Exception: return {"windows": 0}
def screenshot(prefix="accept"):
  try:
    import mss
    ts=time.strftime("%Y%m%d_%H%M%S"); p=SCRN/f"{prefix}_{ts}.png"
    with mss.mss() as s: s.shot(output=str(p))
    return str(p)
  except Exception as e:
    err(f"screenshot:{e}"); return None
# Desktop write
try:
  (DESK/"accept_probe.txt").write_text("ok", encoding="utf-8")
  res["artifacts"]["desktop_write"]=str(DESK/"accept_probe.txt")
except Exception as e: err(f"desktop_write:{e}")
# OpenAI ping
key=os.environ.get("OPENAI_API_KEY","") or (ROOT/"api_key.txt").read_text().strip() if (ROOT/"api_key.txt").exists() else ""
if key:
  try:
    from openai import OpenAI
    client=OpenAI(api_key=key)
    r=client.chat.completions.create(model="gpt-5", messages=[{"role":"user","content":"ping"}], max_completion_tokens=4)
    res["artifacts"]["openai_ok"]=True
  except Exception as e:
    res["artifacts"]["openai_ok"]=False; err(f"openai:{e}")
else:
  res["artifacts"]["openai_ok"]=False
res["artifacts"]["monitors"]=count_monitors()
res["artifacts"]["windows"]=count_windows()
res["artifacts"]["screenshot"]=screenshot("accept")
(RPTS/"ACCEPT_RESULT.json").write_text(json.dumps(res,ensure_ascii=False,indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'gauntlet_accept.py') -Value $ga

# Bring up background cleanly (kept running)
try{ powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null }catch{}
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -HeartbeatSec 2 -HealthSec 2 | Out-Null

# Warm planner + signal tail
& $py dev\core02_planner.py apply | Out-Null
& $py dev\eco_cli.py ask ping | Out-Null

# Tail probe (non-echo assistant)
$deadline=(Get-Date).AddSeconds(90); $tailOk=$false
while((Get-Date) -lt $deadline -and -not $tailOk){
  Start-Sleep -Seconds 3
  $t = try { Get-Content -LiteralPath $tail -Tail 400 -ErrorAction Stop | Out-String } catch { '' }
  if($t -and ($t -match '\[ecosystem\]' -or $t -match 'Bridges ready' -or $t -match 'assistant')){
    if($t -notmatch '^\s*echo:'){ $tailOk=$true }
  }
}

# Soak: 3 pings + 2 Qs
$soakOk=$true
$prompts=@('ping accept1','ping accept2','ping accept3','what is 2+2?','say ok one word only')
foreach($p in $prompts){
  & $py dev\eco_cli.py ask $p | Out-Null
  $ok=$false; $t0=Get-Date
  while(((Get-Date)-$t0).TotalSeconds -lt 25 -and -not $ok){
    Start-Sleep -Seconds 2
    $tt = try { Get-Content -LiteralPath $tail -Tail 250 | Out-String } catch { '' }
    if($tt -and $tt -match '"role"\s*:\s*"assistant"' -and $tt -notmatch '^\s*echo:'){ $ok=$true }
  }
  if(-not $ok){ $soakOk=$false }
}

# Logs check
$stdout=Join-Path $LOGS 'start_stdout.log'
$logOk=$false
if(Test-Path $stdout){
  $chunk = Get-Content -LiteralPath $stdout -Tail 3000 | Out-String
  if($chunk -match 'Desktop Ecosystem ready' -or $chunk -match 'CORE-02 inbox loop started' -or $chunk -match 'JobsWorker started' -or $chunk -match 'Bridges ready'){ $logOk=$true }
}

# Tools/OpenAI via gauntlet
$ga = & $py -m dev.gauntlet_accept
$gaJson=$null; try{ $gaJson=$ga | ConvertFrom-Json }catch{}
$toolsOk=($gaJson -ne $null -and $gaJson.ok)
$openaiOk=($gaJson -ne $null -and $gaJson.artifacts.openai_ok)

# Summary + bundle
$overall = $tailOk -and $logOk -and $soakOk -and $toolsOk
$ts=(Get-Date -Format 'yyyyMMdd_HHmmss')
$sumPath = Join-Path $RPTS 'ACCEPT_SUMMARY.txt'
$bundle   = Join-Path $RUNS ('accept_' + $ts); if(!(Test-Path $bundle)){ New-Item -ItemType Directory -Force -Path $bundle|Out-Null }
$lines=@()
$lines += ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ACCEPTANCE')
$lines += ('tail_ok=' + $tailOk)
$lines += ('logs_ok=' + $logOk)
$lines += ('soak_ok=' + $soakOk)
$lines += ('tools_ok=' + $toolsOk)
$lines += ('openai_ok=' + $openaiOk)
if($gaJson -ne $null){
  $lines += ('monitors=' + $gaJson.artifacts.monitors.monitors)
  $lines += ('windows='  + $gaJson.artifacts.windows.windows)
  $lines += ('screenshot=' + $gaJson.artifacts.screenshot)
  if($gaJson.artifacts.desktop_write){ $lines += ('desktop_write=' + $gaJson.artifacts.desktop_write) }
}
$lines += ('overall_ok=' + $overall)
$lines | Set-Content -Encoding Ascii -LiteralPath $sumPath

# Copy artifacts to bundle + zip
Copy-Item -Force $sumPath $bundle
Copy-Item -Force (Join-Path $RPTS 'STACK_SUMMARY.txt') $bundle -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $RPTS 'STACK_RESULT.json')  $bundle -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $RPTS 'HARD_GAUNTLET_SUMMARY.txt') $bundle -ErrorAction SilentlyContinue
Copy-Item -Force $tail $bundle
if(Test-Path $stdout){ Copy-Item -Force $stdout $bundle }
$stderr=Join-Path $LOGS 'start_stderr.log'; if(Test-Path $stderr){ Copy-Item -Force $stderr $bundle }
Get-ChildItem $SCRN -Filter '*.png' | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object { Copy-Item -Force $_.FullName $bundle }
$zip=Join-Path $RUNS ('accept_' + $ts + '.zip'); if(Test-Path $zip){ Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $bundle '*') -DestinationPath $zip

if($StopAfter){ powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null }

# Exit code reflects success
if($overall){ exit 0 } else { exit 1 }
