param()
# dev/maxcap_closeout.ps1  ASCII-only, idempotent

$ErrorActionPreference='SilentlyContinue'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }

# 1) Post-vacuum DB stats (even if vacuum happened earlier)
try { & $py dev\db_cli.py stats -o runs\db_stats_after_vacuum.json | Out-Null } catch {}

# 2) Derive authoritative pytest summary and append to STATUS.md
$pytestLine = 'unknown'
if (Test-Path 'var\pytest_output.txt') {
  $raw = Get-Content -Path 'var\pytest_output.txt' -Encoding Ascii
  $cand = $raw | Where-Object { $_ -match 'passed' -and $_ -match 'skipped' }
  if ($cand) { $pytestLine = ($cand | Select-Object -Last 1).Trim() }
}
Add-Content -Encoding Ascii -LiteralPath 'STATUS.md' -Value ('pytest: ' + $pytestLine)

# 3) Refresh ASCII task view
try { & $py -c 'from dev import task_tracker_ascii as t; t.write_ascii_tasks()' | Out-Null } catch {}

# 4) Rebuild verification JSON
$drainOk = (Test-Path 'reports\drain_last.out') -and (Select-String -Path 'reports\drain_last.out' -Pattern 'drain_complete' -SimpleMatch -ErrorAction SilentlyContinue)
$hb = (Test-Path 'logs\start_stdout.log') -and (Select-String -Path 'logs\start_stdout.log' -Pattern 'system/heartbeat' -SimpleMatch -ErrorAction SilentlyContinue)
$ver = [pscustomobject]@{
  ts = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  drain_ok = [bool]$drainOk
  tasks_ascii_present = (Test-Path 'reports\TASKS_ASCII.md')
  db_stats_after_vacuum = (Test-Path 'runs\db_stats_after_vacuum.json')
  start_log_has_heartbeat = [bool]$hb
  pytest_summary = $pytestLine
}
$ver | ConvertTo-Json -Depth 5 | Set-Content -Encoding Ascii -LiteralPath 'reports\maxcap_verification.json'

# 5) Optional local commit (no push)
try {
  git add specs\capabilities\*.yaml dev\*.ps1 dev\jobs_drain.py reports\NORTH_STAR.txt STATUS.md 2>$null
  git commit -m 'MAXCAP close-out: db stats, STATUS pytest summary, verification refreshed (no push)' 2>$null
} catch {}

# 6) Breadcrumb + proof bundle
$bundle = 'runs\maxcap_closeout_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach($f in @('runs\db_stats_after_vacuum.json','reports\maxcap_verification.json','reports\TASKS_ASCII.md','STATUS.md')){ if(Test-Path $f){ Copy-Item $f $bundle -Force } }
$lines = @('--- MAXCAP CLOSEOUT ---','timestamp: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),'bundle: ' + $bundle,'ascii_only: true','-----------------------','')
$steps='logs\steps.log'; if(-not (Test-Path $steps)){ New-Item -ItemType File -Path $steps -Force | Out-Null }; Add-Content -Encoding Ascii -LiteralPath $steps -Value ($lines -join [Environment]::NewLine)

Write-Host 'maxcap_closeout complete'
