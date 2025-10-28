$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $repo "logs"
$pidFile = Join-Path $logs "headless_pid.txt"

if (Test-Path $pidFile) {
  try { $pid = [int](Get-Content $pidFile | Select-Object -First 1) } catch { $pid = $null }
  if ($pid -and (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Write-Host ("Stopped headless PID: {0}" -f $pid)
  } else {
    Write-Host "No running headless process found."
  }
  Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
} else {
  Write-Host "No pid file present."
}
