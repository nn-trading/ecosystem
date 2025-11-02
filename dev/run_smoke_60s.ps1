# Run a 60s background smoke, capture logs and summaries (ASCII-only)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

# Begin log
$ops = Join-Path $repo 'runs\current\ops_log.txt'
Add-Content -Encoding ASCII $ops ("SMOKE-60S-BG begin " + (Get-Date -Format 'yyyyMMdd-HHmmss'))

# Stop any background processes
try { .\start.ps1 -Stop 1 | Out-Null } catch {}

# Start background headless for 60s, skip maintenance to reduce lock contention
.\start.ps1 -Headless 1 -Background 1 -RunPytest 0 -StopAfterSec 60 -HeartbeatSec 1 -HealthSec 2 -DoMaintain 0 | Out-Null

# Wait enough time for run to finish and flush
Start-Sleep -Seconds 75

# Stop again to be safe
try { .\start.ps1 -Stop 1 | Out-Null } catch {}

# Capture stdout to runs/current/smoke_60s.txt
$smokePath = Join-Path $repo 'runs\current\smoke_60s.txt'
$stdout = Join-Path $repo 'logs\start_stdout.log'
if (Test-Path $stdout) { Copy-Item -Force $stdout $smokePath } else { Set-Content -Encoding ASCII $smokePath 'no start_stdout.log' }

# Eventlog snapshot (n=200) to runs/current/eventlog_recent.json (ASCII)
$py = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
$snapPath = Join-Path $repo 'runs\current\eventlog_recent.json'
& $py (Join-Path $repo 'dev\eventlog_cli.py') 'snapshot-run' '-n' '200' | Out-File -Encoding ASCII $snapPath

# Create summary with key markers
$summaryPath = Join-Path $repo 'runs\current\smoke_60s_summary.txt'
$sel = Select-String -Path $smokePath -Pattern 'BEGIN','END','Vacuum','Headless','process cannot access' -ErrorAction SilentlyContinue
if ($sel) { $sel | Set-Content -Encoding ASCII $summaryPath } else { Set-Content -Encoding ASCII $summaryPath 'no matches' }

# Record any lingering processes after stop
$procOut = Join-Path $repo 'runs\current\procs_after_stop.txt'
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*\main.py*' }
if ($procs) {
  'PIDs after stop:' | Set-Content -Encoding ASCII $procOut
  foreach ($p in $procs) {
    $line = ("{0} {1}" -f $p.ProcessId, ([string]$p.CommandLine -replace '\s+',' ').Trim())
    Add-Content -Encoding ASCII $procOut $line
  }
} else {
  Set-Content -Encoding ASCII $procOut 'PIDs after stop: none'
}

# End log
Add-Content -Encoding ASCII $ops ("SMOKE-60S-BG end " + (Get-Date -Format 'yyyyMMdd-HHmmss') + " smoke_bytes=" + (Get-Item $smokePath).Length + " snap_bytes=" + (Get-Item $snapPath).Length + " summary_bytes=" + (Get-Item $summaryPath).Length)
