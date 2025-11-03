param()
$ErrorActionPreference = 'Stop'
$devdir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $devdir
Set-Location $repo

# Ensure reports directory
$reports = 'C:\bots\reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$ops = Join-Path $reports 'ops_log.txt'

function Log([string]$msg) {
  $ts = Get-Date -Format s
  Add-Content -Path $ops -Encoding ascii -Value ("["+$ts+"] "+$msg)
}

Log 'BEGIN session: resume Ecosystem AI | DB-UNIFY audit and CLI snapshots'

# DB-UNIFY scan
$scan = Join-Path $reports 'db_unify_scan.txt'
Set-Content -Path $scan -Encoding ascii -Value ("DB-UNIFY scan " + (Get-Date -Format s))
Add-Content -Path $scan -Encoding ascii -Value 'Search terms: ECOSYS_MEMORY_DB, ECOSYS_LOGGER_DB, events.db'
$grep = git grep -n -I -e ECOSYS_MEMORY_DB -e ECOSYS_LOGGER_DB -e events.db -- . 2>$null
$grep | Sort-Object | Out-String -Width 4096 | Add-Content -Path $scan -Encoding ascii
Log ("DB-UNIFY scan written: " + $scan)

# Python resolution
$py = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  $cmd = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($cmd) { $py = $cmd.Source } else { $py = 'python' }
}

# LoggerDB CLI snapshots
& $py dev\loggerdb_cli.py db-path -o (Join-Path $reports 'db_path_snapshot.json') | Out-Null
& $py dev\loggerdb_cli.py stats -o (Join-Path $reports 'loggerdb_stats.json') | Out-Null
& $py dev\loggerdb_cli.py recent -n 20 -o (Join-Path $reports 'loggerdb_recent_20.json') | Out-Null
& $py dev\loggerdb_cli.py search 'system/heartbeat' -n 10 -o (Join-Path $reports 'loggerdb_search_heartbeat.json') | Out-Null
Log 'LoggerDB CLI outputs updated: db_path_snapshot, stats, recent_20, search_heartbeat'
