param()
# dev/maxcap_maintain.ps1  (ASCII-only, idempotent)

$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:LOG_LEVEL='DEBUG'
New-Item -ItemType Directory -Force -Path .\logs, .\runs, .\reports | Out-Null
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }

# 1) Stop background to clear DB locks
try { powershell -NoProfile -File .\start.ps1 -Stop 1 | Out-Null } catch {}

# 2) VACUUM/ANALYZE all known DBs
if (Test-Path '.\maintain.ps1') {
  try { powershell -NoProfile -File .\maintain.ps1 -VacuumDbs 1 | Out-Null } catch {}
}

# 3) Post-vacuum stats
try { & $py dev\db_cli.py stats -o runs\db_stats_after_vacuum.json | Out-Null } catch {}

# 4) Align tasks + regenerate ASCII task view
try { & $py dev\update_tasks_ascii.py | Out-Null } catch {}
try { & $py dev\task_tracker_ascii.py | Out-Null } catch {}

# 5) Restart background headless
try { powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null } catch {}

# 6) Proof bundle + breadcrumbs
$bundle = 'runs\maxcap_maintain_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach ($f in @('runs\db_stats_after_vacuum.json','reports\TASKS_ASCII.md')) { if (Test-Path $f) { Copy-Item $f $bundle -Force } }
$lines = @(
  '--- MAXCAP MAINTAIN ---',
  'timestamp: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),
  'bundle: ' + $bundle,
  'vacuum: attempted',
  'restart: background relaunched',
  'ascii_only: true',
  '------------------------',
  ''
)
$steps='logs\steps.log'; if (-not (Test-Path $steps)) { New-Item -ItemType File -Path $steps -Force | Out-Null }
Add-Content -Encoding Ascii -LiteralPath $steps -Value ($lines -join [Environment]::NewLine)

# 7) Quick visibility (tails)
Write-Host '--- TAIL steps.log ---'
if (Test-Path 'logs\steps.log') { Get-Content -Tail 40 'logs\steps.log' }
Write-Host '--- TAIL start_stdout.log ---'
if (Test-Path 'logs\start_stdout.log') { Get-Content -Tail 40 'logs\start_stdout.log' }

Write-Host 'MAXCAP maintain complete.'
