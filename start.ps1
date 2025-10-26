param(
  [switch]$Headless = $true,
  [int]$StopAfterSec = 0,
  [int]$HeartbeatSec = 5,
  [int]$HealthSec = 60,
  [int]$ResummarizeSec = 300,
  [int]$MemRotateSec = 60,
  [switch]$EnsureVenv = $true,
  [switch]$EnsureDeps = $true,
  [switch]$Background = $true,
  [string]$PythonExe = ""
)
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
Set-Location $repo

# Logs
$logs = Join-Path $repo 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$stdout = Join-Path $logs 'start_stdout.log'
$stderr = Join-Path $logs 'start_stderr.log'
$pidFile = Join-Path $logs 'ecosys_pid.txt'

function Find-Python() {
  param([string]$preferred)
  if ($preferred -and (Test-Path $preferred)) { return $preferred }
  $venvPy = Join-Path $repo '.venv/Scripts/python.exe'
  if (Test-Path $venvPy) { return $venvPy }
  $sysCandidates = @(
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Source,
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1).Source
  ) | Where-Object { $_ -and (Test-Path $_) }
  foreach ($c in $sysCandidates) { return $c }
  return 'python'
}

function Ensure-Venv() {
  $venvPy = Join-Path $repo '.venv/Scripts/python.exe'
  if (Test-Path $venvPy) { return $venvPy }
  $basePy = Find-Python -preferred $PythonExe
  Write-Host "[venv] Creating virtualenv using: $basePy"
  & $basePy -m venv (Join-Path $repo '.venv')
  return (Join-Path $repo '.venv/Scripts/python.exe')
}

function Ensure-Deps([string]$py) {
  Write-Host "[deps] Upgrading pip and installing requirements..."
  & $py -m pip install -U pip | Out-Host
  if (Test-Path (Join-Path $repo 'requirements.txt')) {
    & $py -m pip install -r (Join-Path $repo 'requirements.txt') | Out-Host
  }
}

# Prepare Python
$pyExe = if ($EnsureVenv) { Ensure-Venv } else { Find-Python -preferred $PythonExe }
if ($EnsureDeps) { Ensure-Deps -py $pyExe }

# Build command line with per-process environment via cmd /c
$envParts = @(
  'set ECOSYS_HEADLESS=' + ($(if ($Headless) { '1' } else { '0' })),
  'set STOP_AFTER_SEC=' + $StopAfterSec,
  'set HEARTBEAT_SEC=' + $HeartbeatSec,
  'set HEALTH_SEC=' + $HealthSec,
  'set RESUMMARIZE_SEC=' + $ResummarizeSec,
  'set MEM_ROTATE_SEC=' + $MemRotateSec,
  'set ECOSYS_REPO_ROOT=' + $repo,
  'set ASSISTANT_LOG_DIR=' + $logs,
  'set ECOSYS_ASSISTANT_LOG_DIR=' + $logs,
  'set PYTHONUNBUFFERED=1',
  'set PYTHONIOENCODING=utf-8'
)
$joinedEnv = [string]::Join('&& ', $envParts)
# Use cmd.exe redirection for both modes
$cmdArgs = "/c $joinedEnv && `"$pyExe`" `"$repo\\main.py`" 1>> `"$stdout`" 2>> `"$stderr`""



Write-Host "[start] Repo: $repo"
Write-Host "[start] Python: $pyExe"
Write-Host "[start] Headless: $Headless StopAfterSec: $StopAfterSec"

if ($Background) {
  $p = Start-Process -FilePath 'cmd.exe' -ArgumentList $cmdArgs -WorkingDirectory $repo -WindowStyle Hidden -PassThru
  $childPid = $p.Id
  Set-Content -Path $pidFile -Value $childPid
  Write-Host "[start] Launched background process PID $childPid"
  Write-Host "[start] Stdout: $stdout"
  Write-Host "[start] Stderr: $stderr"
} else {
  & cmd.exe $cmdArgs
}



