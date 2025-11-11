$ErrorActionPreference = 'Stop'
Set-Location 'C:\bots\ecosys'

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$evDir = Join-Path . 'reports\eventlog'
New-Item -ItemType Directory -Force -Path $evDir | Out-Null

# Commit the pytest helper if present (keeps test runs reproducible)
if (Test-Path .\_run_pytest.ps1) {
  git add .\_run_pytest.ps1 | Out-Null
  $diff = git diff --cached --name-only
  if ($diff) {
    git commit -m "chore(test): add _run_pytest.ps1 helper for reproducible local runs`n`nCo-authored-by: openhands <openhands@all-hands.dev>" --author 'openhands <openhands@all-hands.dev>' | Out-Null
  }
}

# Make sure Python is ready
$py = 'C:\bots\ecosys\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'

# Take an EventLog snapshot (200 most recent entries) and save it
$log = Join-Path $evDir ("snapshot_" + $ts + ".txt")
& $py 'dev\eventlog_cli.py' 'snapshot-run' '-n' '200' 2>&1 | Tee-Object -FilePath $log

Write-Host ("OK: EventLog snapshot -> " + (Resolve-Path $log))
