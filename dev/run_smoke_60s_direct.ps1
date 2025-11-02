# Run a 60s foreground smoke, capture logs and summaries (ASCII-only)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

# Begin log
$ops = Join-Path $repo 'runs\current\ops_log.txt'
Add-Content -Encoding ASCII $ops ("SMOKE-60S-DIRECT begin " + (Get-Date -Format 'yyyyMMdd-HHmmss'))

# Stop any running processes
try { .\start.ps1 -Stop 1 | Out-Null } catch {}

# Foreground run for 60 seconds with fast heartbeats; skip maintenance for speed
.\start.ps1 -Headless 1 -Background 0 -RunPytest 0 -StopAfterSec 60 -HeartbeatSec 1 -HealthSec 2 -DoMaintain 0 | Out-Null

# Capture stdout to runs/current/smoke_60s_direct.txt
$smokePath = Join-Path $repo 'runs\current\smoke_60s_direct.txt'
$stdout = Join-Path $repo 'logs\start_stdout.log'
if (Test-Path $stdout) { Copy-Item -Force $stdout $smokePath } else { Set-Content -Encoding ASCII $smokePath 'no start_stdout.log' }

# Create summary with key markers
$summaryPath = Join-Path $repo 'runs\current\smoke_60s_direct_summary.txt'
$sel = Select-String -Path $smokePath -Pattern 'BEGIN','END','Vacuum','Headless','process cannot access' -ErrorAction SilentlyContinue
if ($sel) { $sel | Set-Content -Encoding ASCII $summaryPath } else { Set-Content -Encoding ASCII $summaryPath 'no matches' }

# End log
Add-Content -Encoding ASCII $ops ("SMOKE-60S-DIRECT end " + (Get-Date -Format 'yyyyMMdd-HHmmss') + " smoke_bytes=" + (Get-Item $smokePath).Length + " summary_bytes=" + (Get-Item $summaryPath).Length)
