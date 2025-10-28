$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $repo "logs"
$pidFile = Join-Path $logs "headless_pid.txt"

$pid = $null
if (Test-Path $pidFile) { try { $pid = [int](Get-Content $pidFile | Select-Object -First 1) } catch {} }

if ($pid -and (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
  Write-Host ("Headless running. PID: {0}" -f $pid)
} else {
  Write-Host "Headless not running."
}

# Tail stdout if present
$stdout = Join-Path $logs "headless_stdout.log"
if (Test-Path $stdout) {
  Write-Host "--- stdout (tail 40) ---"
  Get-Content $stdout -Tail 40
}

# Health snapshot
$healthOut = Join-Path $logs "headless_health.json"
if (Test-Path $healthOut) {
  Write-Host "--- health (last 1) ---"
  Get-Content $healthOut -Tail 1
} else {
  Write-Host "(no headless_health.json yet)"
}
