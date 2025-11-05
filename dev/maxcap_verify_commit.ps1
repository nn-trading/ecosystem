param()
# dev/maxcap_verify_commit.ps1  ASCII-only, idempotent

$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:LOG_LEVEL='DEBUG'
New-Item -ItemType Directory -Force -Path .\logs, .\runs, .\reports | Out-Null
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }

# 0) Wait briefly if maintain script is still running
$deadline=(Get-Date).AddSeconds(120)
while($true){ $m=Get-CimInstance Win32_Process | ?{ $_.Name -match 'powershell' -and $_.CommandLine -match 'dev\\maxcap_maintain.ps1' }; if(-not $m -or (Get-Date)-gt $deadline){break}; Start-Sleep 2 }

# 1) Ensure post-vacuum stats exist
if(-not (Test-Path 'runs\db_stats_after_vacuum.json')){ try { & $py dev\db_cli.py stats -o runs\db_stats_after_vacuum.json | Out-Null } catch {} }

# 2) Regenerate ASCII task view
try { & $py dev\update_tasks_ascii.py | Out-Null } catch {}
try { & $py dev\task_tracker_ascii.py | Out-Null } catch {}

# 3) Add bounded jobs drain helper to avoid stuck infinite loops
$dr='dev\jobs_drain.py'
if(-not (Test-Path $dr)){
@'
# dev/jobs_drain.py  (ASCII)
import time, argparse
from dev import jobs_queue as jq
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--loops", type=int, default=5)
    ap.add_argument("--interval", type=float, default=1)
    args=ap.parse_args()
    n=0
    while n<args.loops:
        j=jq.pick_one()
        if j:
            ok,msg=jq.do_job(j)
            jq.complete(j["id"], ok, msg if not ok else "")
        time.sleep(args.interval)
        n+=1
    print("drain_complete")
if __name__=="__main__": main()
'@ | Set-Content -Encoding Ascii -LiteralPath $dr
}

# 4) Quick bounded drain smoke (non-blocking)
try { & $py dev\jobs_drain.py --loops 3 --interval 0.5 | Out-Null } catch {}

# 5) Verification JSON
$hb = (Test-Path 'logs\start_stdout.log') -and (Select-String -Path 'logs\start_stdout.log' -Pattern 'system/heartbeat' -SimpleMatch -ErrorAction SilentlyContinue)
$ver = [pscustomobject]@{
  ts = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  db_stats_after_vacuum = (Test-Path 'runs\db_stats_after_vacuum.json')
  tasks_ascii_present   = (Test-Path 'reports\TASKS_ASCII.md')
  start_log_has_heartbeat = [bool]$hb
}
$ver | ConvertTo-Json -Depth 5 | Set-Content -Encoding Ascii -LiteralPath 'reports\maxcap_verification.json'

# 6) Commit scripts/specs locally (no push)
try {
  git add dev\maxcap_maintain.ps1 dev\jobs_drain.py specs\capabilities\*.yaml reports\NORTH_STAR.txt 2>$null
  git commit -m 'MAXCAP: maintain+verify; seed capability specs; add jobs_drain helper (no push)' 2>$null
} catch {}

# 7) Breadcrumb + tails
$bundle='runs\maxcap_verify_' + (Get-Date -Format 'yyyyMMdd_HHmmss'); New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach($f in @('reports\maxcap_verification.json','runs\db_stats_after_vacuum.json','reports\TASKS_ASCII.md')){ if(Test-Path $f){ Copy-Item $f $bundle -Force } }
$lines=@('--- MAXCAP VERIFY+COMMIT ---','timestamp: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),'bundle: ' + $bundle,'ascii_only: true','----------------------------','')
$steps='logs\steps.log'; if(-not (Test-Path $steps)){ New-Item -ItemType File -Path $steps -Force | Out-Null }; Add-Content -Encoding Ascii -LiteralPath $steps -Value ($lines -join [Environment]::NewLine)

Write-Host '--- TAIL steps.log ---'; if(Test-Path 'logs\steps.log'){ Get-Content -Tail 40 'logs\steps.log' }
Write-Host '--- TAIL start_stdout.log ---'; if(Test-Path 'logs\start_stdout.log'){ Get-Content -Tail 40 'logs\start_stdout.log' }
Write-Host 'MAXCAP verify+commit complete.'
