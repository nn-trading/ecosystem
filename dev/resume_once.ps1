param(
  [int]$StopAfterSec = 12,
  [int]$HeartbeatSec = 1,
  [int]$HealthSec = 5,
  [int]$KeepLast = 50000
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Run-And-Log([string]$cmd) {
  Write-Host "[run_and_log] $cmd"
  & python "$PSScriptRoot\run_and_log.py" $cmd
}

# 1) Start headless (auto-stops after StopAfterSec)
$headlessCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File $PSScriptRoot\start_headless.ps1 -STOP_AFTER_SEC $StopAfterSec -HEARTBEAT_SEC $HeartbeatSec -HEALTH_SEC $HealthSec"
Run-And-Log $headlessCmd

# 2) Probe events and print summary JSON
Run-And-Log "python $PSScriptRoot\probe_events.py"

# 3) Rotate hot events log to keep last $KeepLast lines
Run-And-Log "python $PSScriptRoot\rotate_events.py $KeepLast"

# 4) Local-only commit (if changes)
$needGit = (Get-Command git -ErrorAction SilentlyContinue) -ne $null
if ($needGit) {
  # Ensure user identity exists
  $name = (git -C "$repoRoot" config user.name) 2>$null
  if (-not $name) { git -C "$repoRoot" config user.name "openhands" }
  $email = (git -C "$repoRoot" config user.email) 2>$null
  if (-not $email) { git -C "$repoRoot" config user.email "openhands@all-hands.dev" }

  $status = git -C "$repoRoot" status --porcelain
  if ($status) {
    git -C "$repoRoot" add -A
    git -C "$repoRoot" commit -m "chore: resume cycle run (start headless, probe, rotate, local-commit)" -m "Co-authored-by: openhands <openhands@all-hands.dev>"
    Write-Host "[git] Local commit created."
  } else {
    Write-Host "[git] No changes to commit."
  }
} else {
  Write-Warning "git not found; skipping local commit."
}

Write-Host "[done] resume_once.ps1 completed"