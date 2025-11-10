param([int]$WaitSec=180)
Set-StrictMode -Version 2; $ErrorActionPreference='Stop'
$ROOT='C:\bots\ecosys'; Set-Location -LiteralPath $ROOT
# Stop base background to release tail lock if present
if(Test-Path '.\start.ps1'){ try { powershell -NoProfile -File '.\start.ps1' -Stop 1 | Out-Null } catch {} }
# Stop previous fallback router if running
$forcePids='reports\CORE01_FORCE_TAIL_PIDS.json'
if(Test-Path $forcePids){ try { $fp = Get-Content $forcePids | ConvertFrom-Json -ErrorAction SilentlyContinue; $old=[int]$fp.router_pid; if($old -gt 0){ Stop-Process -Id $old -Force -ErrorAction SilentlyContinue } } catch {} }
function Read-Json($p){ if(Test-Path $p){ try { Get-Content $p -Raw | ConvertFrom-Json } catch { return $null } } }
# venv
$py=Join-Path $ROOT '.venv\Scripts\python.exe'
if(-not (Test-Path $py)){ try{py -3 -m venv .venv}catch{python -m venv .venv}; $py=Join-Path $ROOT '.venv\Scripts\python.exe' }
# stop existing router
$p1=Read-Json 'reports\CORE01_FIX_PIDS.json'
$p2=Read-Json 'reports\AUTONOMOUS_PIDS.json'
$router_pid=0
if($p1 -and $p1.router){ $router_pid=[int]$p1.router } elseif($p1 -and $p1.router_pid){ $router_pid=[int]$p1.router_pid } elseif($p2 -and $p2.router){ $router_pid=[int]$p2.router }
if($router_pid -gt 0){ try{ Stop-Process -Id $router_pid -Force -ErrorAction SilentlyContinue }catch{} }
# write fallback router
$router_py=@'
import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TAIL   = ROOT / "reports/chat/exact_tail.jsonl"
SHADOW = ROOT / "reports/chat/exact_tail_shadow.jsonl"
ROUTE  = ROOT / "reports/ROUTER_EVENTS.jsonl"

def append_tail(obj):
    try:
        TAIL.parent.mkdir(parents=True, exist_ok=True)
        with TAIL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=True)+"\n")
    except Exception:
        SHADOW.parent.mkdir(parents=True, exist_ok=True)
        with SHADOW.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=True)+"\n")

def log_route(obj):
    ROUTE.parent.mkdir(parents=True, exist_ok=True)
    with ROUTE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True)+"\n")

def to_call(text):
    t=(text or '').lower()
    if 'screenshot' in t:
        return {'tool':'screenshot','args':{}}
    if 'monitor' in t or 'screen' in t:
        return {'tool':'monitors','args':{}}
    if 'window' in t:
        return {'tool':'windows','args':{}}
    return {'tool':'write','args':{'text': (text or '')[:500]}}

def main():
    TAIL.parent.mkdir(parents=True, exist_ok=True)
    TAIL.touch(exist_ok=True)
    pos=0
    while True:
        try:
            with TAIL.open('r', encoding='utf-8') as f:
                f.seek(pos)
                for line in f:
                    pos=f.tell()
                    try:
                        obj=json.loads(line)
                    except Exception:
                        continue
                    if obj.get('role')=='user' and obj.get('text'):
                        call=to_call(obj['text'])
                        append_tail({'ts': time.time(), 'role':'assistant', 'text': '[ecosystem-call] '+json.dumps(call, ensure_ascii=True)})
                        log_route({'ts': time.time(), 'route':'fallback', 'text': obj['text'], 'call': call})
        except Exception:
            time.sleep(0.5)
        time.sleep(0.5)

if __name__=='__main__':
    main()
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\nl_router_fallback.py' -Value $router_py
# start fallback router
$log=Join-Path $ROOT ("reports\\router_fallback_" + (Get-Date -Format yyyyMMdd_HHmmss) + ".log")
$sp=Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory $ROOT -FilePath $py -ArgumentList 'dev\nl_router_fallback.py' -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
$rpid=$sp.Id
@{ router_pid=$rpid; ts=(Get-Date -Format s); log=$log } | ConvertTo-Json | Set-Content -Encoding Ascii -LiteralPath 'reports\CORE01_FORCE_TAIL_PIDS.json'
# inject one user line
$inject=@'
import json, time
from pathlib import Path
p=Path('reports/chat/exact_tail.jsonl')
p.parent.mkdir(parents=True, exist_ok=True)
p.touch(exist_ok=True)
line={'ts': time.time(), 'role':'user', 'text':'count monitors only'}
with p.open('a', encoding='utf-8') as f:
    f.write(json.dumps(line, ensure_ascii=True)+'\n')
print('injected')
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\tail_inject_once.py' -Value $inject
# also inject one assistant ecosystem-call line to trigger dispatcher directly
$callpy=@'
import json, time
from pathlib import Path
p=Path('reports/chat/exact_tail.jsonl')
p.parent.mkdir(parents=True, exist_ok=True)
p.touch(exist_ok=True)
obj={'ts': time.time(), 'role':'assistant', 'text':'[ecosystem-call] ' + json.dumps({'tool':'monitors','args':{}}, ensure_ascii=True)}
with p.open('a', encoding='utf-8') as f:
    f.write(json.dumps(obj, ensure_ascii=True)+'\n')
print('call-injected')
'@
Set-Content -Encoding Ascii -LiteralPath 'dev\append_call_once.py' -Value $callpy
& $py 'dev\append_call_once.py' | Out-Null

& $py 'dev\tail_inject_once.py' | Out-Null
# wait for ecosystem-result
$deadline=(Get-Date).AddSeconds($WaitSec); $ok=$false
while((Get-Date) -lt $deadline){
  Start-Sleep -Milliseconds 800
  if(Test-Path 'reports\chat\exact_tail.jsonl'){
    if(Select-String -Path 'reports\chat\exact_tail.jsonl' -SimpleMatch -Pattern '[ecosystem-result]' -Quiet){ $ok=$true; break }
  }
  if(Test-Path 'reports\chat\exact_tail_shadow.jsonl'){
    if(Select-String -Path 'reports\chat\exact_tail_shadow.jsonl' -SimpleMatch -Pattern '[ecosystem-result]' -Quiet){ $ok=$true; break }
  }
}
$sum="=== CORE-01 FORCE-TAIL === ok=$ok router_pid=$rpid"
Set-Content -Encoding Ascii -LiteralPath 'reports\CORE01_FORCE_TAIL_SUMMARY.txt' -Value $sum
Write-Host $sum
