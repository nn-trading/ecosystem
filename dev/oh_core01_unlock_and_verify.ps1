param([switch]$KeepRunning=$true, [int]$WaitStandard=90, [int]$WaitFallback=90)
$ErrorActionPreference='Stop'
$root = 'C:\bots\ecosys'
Set-Location -LiteralPath $root

function ReadJson($p){ if(Test-Path $p){ try{ Get-Content $p -Raw | ConvertFrom-Json }catch{ $null } } }
function KillPid($pid){ if($pid -gt 0){ try{ Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }catch{} } }
function EnsureDir($p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function WriteAscii($path,$text){ Set-Content -Encoding Ascii -LiteralPath $path -Value $text }
function TailHasResult{
  param([string]$path)
  if(Test-Path $path){ return [bool](Select-String -Path $path -SimpleMatch -Pattern '[ecosystem-result]' -Quiet) }
  return $false
}

# --- Stop anything holding the tail or ports (using PID files only, safe) ---
$p = ReadJson '.\reports\AUTONOMOUS_PIDS.json'
$pf = ReadJson '.\reports\CORE01_FORCE_TAIL_PIDS.json'
$pf2= ReadJson '.\reports\CORE01_FIX_PIDS.json'
foreach($cand in @(
  $p?.tool, $p?.dispatch, $p?.router,
  $pf?.router_pid,
  $pf2?.tool_server_pid, $pf2?.dispatcher_pid, $pf2?.router_pid
)){ if($cand){ KillPid([int]$cand) } }

# --- Ensure folders + dual ASCII configs ---
EnsureDir '.\config'; EnsureDir '.\configs'; EnsureDir '.\reports\chat'; EnsureDir '.\logs'; EnsureDir '.\dev'
WriteAscii '.\config\model.yaml'  "default: gpt-5`r`nlock: true"
WriteAscii '.\configs\model.yaml' "default: gpt-5`r`nlock: true"
WriteAscii '.\config\comms.yaml'  "mode: brain`r`necho: false`r`ntail: reports/chat/exact_tail.jsonl"
WriteAscii '.\configs\comms.yaml' "mode: brain`r`necho: false`r`ntail: reports/chat/exact_tail.jsonl"

# --- Fresh tail (archive if present) ---
$ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
EnsureDir '.\reports\archive\chat'
if(Test-Path '.\reports\chat\exact_tail.jsonl'){
  try{ Move-Item '.\reports\chat\exact_tail.jsonl' ('.\reports\archive\chat\exact_tail_'+$ts+'.jsonl') -Force }catch{}
}
'' | Set-Content -Encoding Ascii -LiteralPath '.\reports\chat\exact_tail.jsonl'
# Shadow is optional; leave as-is if present.

# --- Ensure venv + deps ---
$py = '.\.venv\Scripts\python.exe'
if(-not (Test-Path $py)){ python -m venv .venv | Out-Null; $py = '.\.venv\Scripts\python.exe' }
& $py -m pip install --disable-pip-version-check -q --upgrade pip > $null 2>&1
& $py -m pip install -q fastapi uvicorn requests 'openai>=1,<2' > $null 2>&1

# --- Sanity: required modules must exist ---
if(-not (Test-Path '.\dev\tool_server.py') -or -not (Test-Path '.\dev\dispatcher.py')){
  throw 'Missing dev\tool_server.py or dev\dispatcher.py'
}

# --- Start standard stack ---
$tool = Start-Process -FilePath $py -ArgumentList '-m','uvicorn','dev.tool_server:app','--host','127.0.0.1','--port','8766' -WindowStyle Hidden -PassThru
$dispatch = Start-Process -FilePath $py -ArgumentList 'dev\dispatcher.py' -WindowStyle Hidden -PassThru
$router = $null
if(Test-Path '.\dev\nl_router.py'){
  $router = Start-Process -FilePath $py -ArgumentList 'dev\nl_router.py' -WindowStyle Hidden -PassThru
}

# --- Ping tool server readiness ---
$deadline = (Get-Date).AddSeconds(30)
$tool_ok=$false
while((Get-Date)-lt $deadline){
  try{
    $pong = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8766/ping' -TimeoutSec 5
    if($pong.Content -match '"ok":\s*true'){ $tool_ok=$true; break }
  }catch{}
  Start-Sleep -Milliseconds 400
}
if(-not $tool_ok){ throw 'Tool server not responding on /ping' }

# --- Helper: safe tail inject via Python ---
$inject_py = @'
import json, time
from pathlib import Path
p = Path("reports/chat/exact_tail.jsonl")
p.parent.mkdir(parents=True, exist_ok=True)
p.touch(exist_ok=True)
def add(text):
    line = {"ts": time.time(), "role":"user", "text": text}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False)+"\n")
add("please write a desktop note and take a screenshot")
'@
Set-Content -Encoding Ascii -LiteralPath '.\dev\tail_inject_once.py' -Value $inject_py
& $py '.\dev\tail_inject_once.py' | Out-Null

# --- Wait for standard router -> dispatcher -> result ---
$ok=$false; $source=''; $std_deadline=(Get-Date).AddSeconds($WaitStandard)
while((Get-Date)-lt $std_deadline){
  Start-Sleep -Milliseconds 700
  if(TailHasResult '.\reports\chat\exact_tail.jsonl' -or TailHasResult '.\reports\chat\exact_tail_shadow.jsonl'){
    $ok=$true; $source='standard'; break
  }
}

# --- Fallback router if needed ---
$fallback_pid=0
if(-not $ok){
  # write deterministic fallback router
  $fallback = @'
import json, time
from pathlib import Path
TAIL=Path("reports/chat/exact_tail.jsonl"); SHADOW=Path("reports/chat/exact_tail_shadow.jsonl"); ROUTE=Path("reports/ROUTER_EVENTS.jsonl")
def append_tail(obj):
    try:
        TAIL.parent.mkdir(parents=True, exist_ok=True)
        with TAIL.open("a", encoding="utf-8") as f: f.write(json.dumps(obj, ensure_ascii=False)+"\n")
    except Exception:
        SHADOW.parent.mkdir(parents=True, exist_ok=True)
        with SHADOW.open("a", encoding="utf-8") as f: f.write(json.dumps(obj, ensure_ascii=False)+"\n")
def log_route(obj):
    ROUTE.parent.mkdir(parents=True, exist_ok=True)
    with ROUTE.open("a", encoding="utf-8") as f: f.write(json.dumps(obj, ensure_ascii=False)+"\n")
def to_call(text):
    t=(text or '').lower()
    if 'screenshot' in t: return {'tool':'screenshot','args':{}}
    if 'monitor' in t or 'screen' in t: return {'tool':'monitors','args':{}}
    if 'window' in t: return {'tool':'windows','args':{}}
    return {'tool':'write','args':{'stem':'auto_note','text':(text or '')[:500]}}
def main():
    pos=0
    TAIL.parent.mkdir(parents=True, exist_ok=True); TAIL.touch(exist_ok=True)
    while True:
        try:
            with TAIL.open('r', encoding='utf-8') as f:
                f.seek(pos)
                for line in f:
                    pos=f.tell()
                    try: obj=json.loads(line)
                    except: continue
                    if obj.get('role')=='user' and obj.get('text'):
                        call=to_call(obj['text'])
                        append_tail({'ts': time.time(),'role':'assistant','text':'[ecosystem-call] '+json.dumps(call, ensure_ascii=False)})
                        log_route({'ts': time.time(),'route':'fallback','text':obj['text'],'call':call})
        except Exception:
            time.sleep(0.5)
        time.sleep(0.5)
if __name__=='__main__': main()
'@
  Set-Content -Encoding Ascii -LiteralPath '.\dev\nl_router_fallback.py' -Value $fallback
  $fb = Start-Process -FilePath $py -ArgumentList 'dev\nl_router_fallback.py' -WindowStyle Hidden -PassThru
  $fallback_pid = $fb.Id
  # inject a second line for fallback to consume
  $inject2 = @'
import json, time
from pathlib import Path
p=Path("reports/chat/exact_tail.jsonl"); p.parent.mkdir(parents=True, exist_ok=True); p.touch(exist_ok=True)
line={"ts": time.time(), "role":"user", "text":"fallback route: write autonote and take screenshot"}
with p.open("a", encoding="utf-8") as f: f.write(json.dumps(line, ensure_ascii=False)+"\n")
'@
  Set-Content -Encoding Ascii -LiteralPath '.\dev\tail_inject_fallback.py' -Value $inject2
  & $py '.\dev\tail_inject_fallback.py' | Out-Null
  $fb_deadline=(Get-Date).AddSeconds($WaitFallback)
  while((Get-Date)-lt $fb_deadline){
    Start-Sleep -Milliseconds 700
    if(TailHasResult '.\reports\chat\exact_tail.jsonl' -or TailHasResult '.\reports\chat\exact_tail_shadow.jsonl'){
      $ok=$true; $source='fallback'; break
    }
  }
}

# --- Persist PIDs and summary ---
$info = @{
  tool_server_pid = $tool.Id
  dispatcher_pid  = $dispatch.Id
  router_pid      = ($router?.Id) | ForEach-Object { $_ } 
  fallback_pid    = $fallback_pid
  ts = (Get-Date).ToString('s')
}
$info | ConvertTo-Json | WriteAscii '.\reports\CORE01_UNLOCK_PIDS.json'
$summary = "=== CORE-01 UNLOCK+VERIFY === ok=$ok source=$source tool=$($tool.Id) dispatch=$($dispatch.Id) router=$($router?.Id) fallback=$fallback_pid"
WriteAscii '.\reports\CORE01_UNLOCK_VERIFY.txt' $summary
Write-Host $summary

# --- Stop or keep running ---
if(-not $KeepRunning){
  KillPid $fallback_pid
  if($router){ KillPid $router.Id }
  KillPid $dispatch.Id
  KillPid $tool.Id
}
