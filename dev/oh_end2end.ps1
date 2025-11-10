param([switch]$StopAfter = $true)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'

# ---- Paths / ensure dirs ----
$ROOT='C:\bots\ecosys'; $DEV=Join-Path $ROOT 'dev'; $CFG=Join-Path $ROOT 'config'
$RPTS=Join-Path $ROOT 'reports'; $CHAT=Join-Path $RPTS 'chat'; $SCRN=Join-Path $RPTS 'screens'
$LOGS=Join-Path $ROOT 'logs'; $RUNS=Join-Path $ROOT 'runs'
$LARCH=Join-Path $LOGS 'archive'; $RARCH=Join-Path $RPTS 'archive'; $CARCH=Join-Path $RARCH 'chat'
$dirs=@($ROOT,$DEV,$CFG,$RPTS,$CHAT,$SCRN,$LOGS,$RUNS,$LARCH,$RARCH,$CARCH); foreach($d in $dirs){ if(!(Test-Path $d)){ New-Item -ItemType Directory -Force -Path $d|Out-Null } }
if(!(Test-Path (Join-Path $DEV '__init__.py'))){ ''|Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV '__init__.py') }
$tail=Join-Path $CHAT 'exact_tail.jsonl'

# ---- Enforce config (correct folder: config\) ----
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'model.yaml') @'
default: gpt-5
lock: true
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $CFG 'comms.yaml') @'
mode: brain
echo: false
tail: reports/chat/exact_tail.jsonl
'@

# ---- Ensure services stopped before rotation ----
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
Start-Sleep -Seconds 2

# ---- Ensure services stopped before rotation ----
try { powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null } catch {}
Start-Sleep -Seconds 2

# ---- Rotate logs & tail to avoid legacy spam ----
$ts=(Get-Date -Format 'yyyyMMdd_HHmmss')
$stdout=Join-Path $LOGS 'start_stdout.log'; if(Test-Path $stdout){ Move-Item -Force $stdout (Join-Path $LARCH ('start_stdout_'+$ts+'.log')) }
$stderr=Join-Path $LOGS 'start_stderr.log'; if(Test-Path $stderr){ Move-Item -Force $stderr (Join-Path $LARCH ('start_stderr_'+$ts+'.log')) }
if(Test-Path $tail){ Move-Item -Force $tail (Join-Path $CARCH ('exact_tail_'+$ts+'.jsonl')) }
''|Set-Content -Encoding Ascii -LiteralPath $tail

# ---- Python + deps ----
$py=Join-Path $ROOT '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  if(Get-Command py -ErrorAction SilentlyContinue){ py -3 -m venv (Join-Path $ROOT '.venv') } else { python -m venv (Join-Path $ROOT '.venv') }
  $py=Join-Path $ROOT '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip | Out-Null
& $py -m pip install --upgrade --quiet 'openai>=1,<2' psutil pywin32 mss pillow screeninfo keyboard requests pyautogui | Out-Null

# ---- E2E Gauntlet Python (UI + API + FS) ----
$pySrc=@'
import os, json, time, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RPTS=ROOT/"reports"; CHAT=RPTS/"chat"; SCRN=RPTS/"screens"; DESK=Path(os.path.expanduser("~"))/"Desktop"
RPTS.mkdir(parents=True, exist_ok=True); CHAT.mkdir(parents=True, exist_ok=True); SCRN.mkdir(parents=True, exist_ok=True)
res={"ok": True, "errors": [], "artifacts": {}}
def err(m): res["errors"].append(str(m)); res["ok"]=False

# monitors/windows
def count_monitors():
    try:
        from screeninfo import get_monitors
        return {"monitors": len(get_monitors())}
    except Exception as e:
        return {"monitors": 0}
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
    except Exception:
        return {"windows": 0}

# screenshot
def screenshot(prefix="e2e"):
    try:
        import mss
        ts=time.strftime("%Y%m%d_%H%M%S"); p=SCRN/f"{prefix}_{ts}.png"
        with mss.mss() as s: s.shot(output=str(p))
        return str(p)
    except Exception as e:
        err(f"screenshot:{e}"); return None

# desktop write
try:
    (DESK/"e2e_probe.txt").write_text("OK", encoding="utf-8")
    res["artifacts"]["desktop_write"]=str(DESK/"e2e_probe.txt")
except Exception as e:
    err(f"desktop_write:{e}")

# optional notepad automation (best-effort)
try:
    import pyautogui, time as _t
    p = subprocess.Popen(["notepad.exe"])
    _t.sleep(1.5)
    pyautogui.typewrite("E2E NOTEPAD OK", interval=0.02)
    pyautogui.hotkey("ctrl","s"); _t.sleep(0.8)
    save_path = str(DESK/"e2e_notepad.txt")
    pyautogui.typewrite(save_path, interval=0.01); _t.sleep(0.4)
    pyautogui.press("enter"); _t.sleep(0.6)
    res["artifacts"]["notepad_saved"]=save_path
    try: p.terminate()
    except: pass
except Exception as e:
    # not critical; record and continue
    res["artifacts"]["notepad_saved"]=False
    res["errors"].append(f"notepad:{e}")

# OpenAI ping (uses env or api_key.txt)
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
res["artifacts"]["screenshot"]=screenshot("e2e")
(RPTS/"E2E_RESULT.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res))
'@
Set-Content -Encoding Ascii -LiteralPath (Join-Path $DEV 'gauntlet_e2e.py') -Value $pySrc

# ---- Clean start background ----
try{ powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null }catch{}
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -HeartbeatSec 2 -HealthSec 2 | Out-Null

# ---- Warm planner + seed tail ----
& $py dev\core02_planner.py apply | Out-Null
& $py dev\eco_cli.py ask ping | Out-Null

# ---- Tail probe (must see assistant, not echo, and no retry spam) ----
$deadline=(Get-Date).AddSeconds(90); $tailOk=$false
$noSpam=$true
while((Get-Date) -lt $deadline -and -not $tailOk){
  Start-Sleep -Seconds 3
  $blob = try { Get-Content -LiteralPath $tail -Tail 400 -ErrorAction Stop | Out-String } catch { '' }
  if($blob){
    if($blob -match 'retry budget exhausted' -or $blob -match '\[Worker\]\s*Replan'){ $noSpam=$false }
    if(($blob -match '"role"\s*:\s*"assistant"' -or $blob -match '\[ecosystem\]') -and $blob -notmatch '^\s*echo:'){ $tailOk=$true }
  }
}

# ---- Soak: multiple prompts, require assistant lines ----
$soakOk=$true
$prompts=@('ping e2e1','ping e2e2','what is 2+2?','respond with word OK only')
foreach($p in $prompts){
  & $py dev\eco_cli.py ask $p | Out-Null
  $ok=$false; $t0=Get-Date
  while(((Get-Date)-$t0).TotalSeconds -lt 25 -and -not $ok){
    Start-Sleep -Seconds 2
    $tt = try { Get-Content -LiteralPath $tail -Tail 300 | Out-String } catch { '' }
    if($tt -and $tt -match '"role"\s*:\s*"assistant"' -and $tt -notmatch '^\s*echo:' -and $tt -notmatch 'retry budget exhausted' -and $tt -notmatch '\[Worker\]\s*Replan'){ $ok=$true }
  }
  if(-not $ok){ $soakOk=$false }
}

# ---- Logs check ----
$stdout=Join-Path $LOGS 'start_stdout.log'
$logOk=$false
if(Test-Path $stdout){
  $chunk = Get-Content -LiteralPath $stdout -Tail 4000 | Out-String
  if($chunk -match 'Desktop Ecosystem ready' -or $chunk -match 'CORE-02 inbox loop started' -or $chunk -match 'JobsWorker started' -or $chunk -match 'Bridges ready'){ $logOk=$true }
  if($chunk -match 'retry budget exhausted' -or $chunk -match '\[Worker\]\s*Replan'){ $noSpam=$false }
}

# ---- Tools & OpenAI via gauntlet ----
$ga = & $py -m dev.gauntlet_e2e
$gaJson=$null; try{ $gaJson=$ga | ConvertFrom-Json }catch{}
$toolsOk=($gaJson -ne $null -and $gaJson.ok)
$openaiOk=($gaJson -ne $null -and $gaJson.artifacts.openai_ok)

# ---- Decide overall ----
$overall = $tailOk -and $logOk -and $soakOk -and $toolsOk -and $noSpam

# ---- Summaries + bundle ----
$ts=(Get-Date -Format 'yyyyMMdd_HHmmss')
$sumPath = Join-Path $RPTS 'E2E_SUMMARY.txt'
$lines=@()
$lines += ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] E2E')
$lines += ('tail_ok=' + $tailOk)
$lines += ('logs_ok=' + $logOk)
$lines += ('soak_ok=' + $soakOk)
$lines += ('tools_ok=' + $toolsOk)
$lines += ('openai_ok=' + $openaiOk)
$lines += ('no_retry_spam=' + $noSpam)
if($gaJson -ne $null){
  if($gaJson.artifacts.monitors){ $lines += ('monitors=' + $gaJson.artifacts.monitors.monitors) }
  if($gaJson.artifacts.windows){  $lines += ('windows='  + $gaJson.artifacts.windows.windows) }
  if($gaJson.artifacts.screenshot){ $lines += ('screenshot=' + $gaJson.artifacts.screenshot) }
  if('desktop_write' -in $gaJson.artifacts.Keys){ $lines += ('desktop_write=' + $gaJson.artifacts.desktop_write) }
  if('notepad_saved' -in $gaJson.artifacts.Keys){ $lines += ('notepad_saved=' + $gaJson.artifacts.notepad_saved) }
}
$lines += ('overall_ok=' + $overall)
$lines | Set-Content -Encoding Ascii -LiteralPath $sumPath

$bundle   = Join-Path $RUNS ('e2e_' + $ts); if(!(Test-Path $bundle)){ New-Item -ItemType Directory -Force -Path $bundle|Out-Null }
Copy-Item -Force $sumPath $bundle
Copy-Item -Force (Join-Path $RPTS 'ACCEPT_SUMMARY.txt') $bundle -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $RPTS 'STACK_SUMMARY.txt')   $bundle -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $RPTS 'HARD_GAUNTLET_SUMMARY.txt') $bundle -ErrorAction SilentlyContinue
Copy-Item -Force (Join-Path $RPTS 'E2E_RESULT.json') $bundle -ErrorAction SilentlyContinue
Copy-Item -Force $tail $bundle
$stdout=Join-Path $LOGS 'start_stdout.log'; if(Test-Path $stdout){ Copy-Item -Force $stdout $bundle }
$stderr=Join-Path $LOGS 'start_stderr.log'; if(Test-Path $stderr){ Copy-Item -Force $stderr $bundle }
Get-ChildItem $SCRN -Filter '*.png' | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | % { Copy-Item -Force $_.FullName $bundle }
$zip=Join-Path $RUNS ('e2e_' + $ts + '.zip'); if(Test-Path $zip){ Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $bundle '*') -DestinationPath $zip

if($StopAfter){ powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null }
if($overall){ exit 0 } else { exit 1 }
