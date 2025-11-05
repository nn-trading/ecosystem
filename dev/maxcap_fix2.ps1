param()
# dev/maxcap_fix2.ps1  ASCII-only, idempotent

$ErrorActionPreference = 'SilentlyContinue'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:LOG_LEVEL='DEBUG'
New-Item -ItemType Directory -Force -Path .\logs, .\runs, .\reports | Out-Null
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }

# 1) Robust jobs_drain helper (fix import path when run as a script)
$dr='dev\jobs_drain.py'
@'
# dev/jobs_drain.py (ASCII)
import sys, time, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rp = str(ROOT)
if rp not in sys.path:
    sys.path.insert(0, rp)

try:
    from dev import jobs_queue as jq
except Exception:
    try:
        import jobs_queue as jq  # fallback if run from project root
    except Exception as e:
        print("import_error:", e)
        raise

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops", type=int, default=5)
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()
    n = 0
    while n < args.loops:
        j = jq.pick_one()
        if j:
            ok, msg = jq.do_job(j)
            jq.complete(j["id"], ok, msg if not ok else "")
        time.sleep(args.interval)
        n += 1
    print("drain_complete")

if __name__ == "__main__":
    main()
'@ | Set-Content -Encoding Ascii -LiteralPath $dr

# 2) Quick bounded drain smoke (non-blocking)
$drOut = & $py dev\jobs_drain.py --loops 3 --interval 0.5 2>&1
Set-Content -Encoding Ascii -LiteralPath 'reports\drain_last.out' -Value ($drOut | Out-String)

# 3) (Re)write verification JSON
$hb = (Test-Path 'logs\start_stdout.log') -and (Select-String -Path 'logs\start_stdout.log' -Pattern 'system/heartbeat' -SimpleMatch -ErrorAction SilentlyContinue)
$ver = [pscustomobject]@{
  ts = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  drain_ok = [bool]($drOut -match 'drain_complete')
  tasks_ascii_present = (Test-Path 'reports\TASKS_ASCII.md')
  db_stats_after_vacuum = (Test-Path 'runs\db_stats_after_vacuum.json')
  start_log_has_heartbeat = [bool]$hb
}
$ver | ConvertTo-Json -Depth 5 | Set-Content -Encoding Ascii -LiteralPath 'reports\maxcap_verification.json'

# 4) Amend last commit with Co-authored-by (no push)
try {
  $msg = (git log -1 --pretty=%B)
  if ($msg -notmatch 'Co-authored-by:\s*openhands') {
    $new = "$msg`r`nCo-authored-by: openhands <openhands@all-hands.dev>"
    git commit --amend -m "$new" 2>$null
  }
} catch {}

# 5) Breadcrumb + small bundle
$bundle = 'runs\maxcap_fix2_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach($f in @('reports\maxcap_verification.json','reports\drain_last.out')){ if(Test-Path $f){ Copy-Item $f $bundle -Force } }
$lines=@('--- MAXCAP FIX2 ---','timestamp: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),'bundle: ' + $bundle,'ascii_only: true','-------------------','')
$steps='logs\steps.log'; if(-not (Test-Path $steps)){ New-Item -ItemType File -Path $steps -Force | Out-Null }; Add-Content -Encoding Ascii -LiteralPath $steps -Value ($lines -join [Environment]::NewLine)

Write-Host '--- TAIL steps.log ---'; if(Test-Path 'logs\steps.log'){ Get-Content -Tail 30 'logs\steps.log' }
Write-Host '--- TAIL start_stdout.log ---'; if(Test-Path 'logs\start_stdout.log'){ Get-Content -Tail 30 'logs\start_stdout.log' }
Write-Host 'MAXCAP fix2 complete.'
