param(
  [int]$STOP_AFTER_SEC = $(if ($env:STOP_AFTER_SEC) { [int]$env:STOP_AFTER_SEC } else { 12 }),
  [int]$HEARTBEAT_SEC = $(if ($env:HEARTBEAT_SEC) { [int]$env:HEARTBEAT_SEC } else { 1 }),
  [int]$HEALTH_SEC = $(if ($env:HEALTH_SEC) { [int]$env:HEALTH_SEC } else { 5 })
)
$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $repo "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$pidFile = Join-Path $logs "headless_pid.txt"

# Skip if already running
$existing = $null
if (Test-Path $pidFile) {
  try { $existing = [int](Get-Content $pidFile | Select-Object -First 1) } catch {}
}
if ($existing -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)) {
  Write-Host "Headless already running (PID $existing). Skipping start."
  exit 0
}

[System.Environment]::SetEnvironmentVariable("ECOSYS_HEADLESS","1","Process")
[System.Environment]::SetEnvironmentVariable("ENABLE_JSONL_RECORDER","1","Process")
[System.Environment]::SetEnvironmentVariable("STOP_AFTER_SEC",$STOP_AFTER_SEC.ToString(),"Process")
[System.Environment]::SetEnvironmentVariable("HEARTBEAT_SEC",$HEARTBEAT_SEC.ToString(),"Process")
[System.Environment]::SetEnvironmentVariable("HEALTH_SEC",$HEALTH_SEC.ToString(),"Process")

$stdout = Join-Path $logs "headless_stdout.log"
$stderr = Join-Path $logs "headless_stderr.log"

$p = Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $repo -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$pid = $p.Id
Set-Content -Path $pidFile -Value $pid

Start-Sleep -Seconds $STOP_AFTER_SEC
if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
  Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  $stopped = $true
} else {
  $stopped = $false
}

# Write a health snapshot to logs/headless_health.json (ASCII-safe)
$healthOut = Join-Path $logs "headless_health.json"
try {
  Push-Location $repo
  & python "dev/health_check.py" | Out-File -FilePath $healthOut -Encoding ascii -Append
  Pop-Location
} catch {}

# Clean up stale pid file if stopped
if ($stopped -or -not (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
  Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
}

Write-Host ("Started PID {0} for {1}s. Stopped:{2}" -f $pid, $STOP_AFTER_SEC, $stopped)
