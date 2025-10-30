param(
  [string]$Headless = '1',
  [int]$StopAfterSec = 0,
  [int]$HeartbeatSec = 5,
  [int]$HealthSec = 60,
  [int]$ResummarizeSec = 300,
  [int]$MemRotateSec = 60,
  [string]$EnsureVenv = '1',
  [string]$EnsureDeps = '0',
  [string]$Background = '1',
  [string]$PythonExe = "",
  [string]$Stop = '0',
  [string]$RunPytest = '0'
)
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
Set-Location $repo

function To-Bool([Object]$x) {
  if ($x -is [bool]) { return $x }
  if ($x -is [System.Management.Automation.SwitchParameter]) { return [bool]$x }
  $s = [string]$x
  if (-not $s) { return $false }
  $s = $s.Trim().ToLower()
  return ($s -eq '1' -or $s -eq 'true' -or $s -eq 'yes' -or $s -eq 'on')
}

$HeadlessB = To-Bool $Headless
$EnsureVenvB = To-Bool $EnsureVenv
$EnsureDepsB = To-Bool $EnsureDeps
$BackgroundB = To-Bool $Background
$StopB = To-Bool $Stop
$RunPytestB = To-Bool $RunPytest


# Logs
$logs = Join-Path $repo 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$stdout = Join-Path $logs 'start_stdout.log'
$stderr = Join-Path $logs 'start_stderr.log'
$pidFile = Join-Path $logs 'ecosys_pid.txt'

# Optional stop helper
if ($StopB) {
  $stopped = @()
  $headlessPidFile = Join-Path $logs 'headless_pid.txt'
  if (Test-Path $headlessPidFile) {
    try {
      $pid = Get-Content $headlessPidFile | Select-Object -First 1
      if ($pid) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue; $stopped += $pid }
    } catch {}
    try { Remove-Item $headlessPidFile -ErrorAction SilentlyContinue } catch {}
  }
  if (Test-Path $pidFile) {
    try {
      $pid = Get-Content $pidFile | Select-Object -First 1
      if ($pid) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue; $stopped += $pid }
    } catch {}
    try { Remove-Item $pidFile -ErrorAction SilentlyContinue } catch {}
  }
  Write-Host ("[stop] Stopped PIDs: {0}" -f ($stopped -join ', '))
  return
}

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
$pyExe = if ($EnsureVenvB) { Ensure-Venv } else { Find-Python -preferred $PythonExe }
if ($EnsureDepsB) { Ensure-Deps -py $pyExe }


# Pre-start maintenance: purge logs, vacuum DBs, optionally run pytest
try {
  Write-Host "[start] Running pre-start maintenance (purge logs, vacuum, pytest:$RunPytest)..."
  & (Join-Path $repo 'maintain.ps1') -PurgeLogs -VacuumDbs -Restart:$false -EnsureDeps:$EnsureDepsB -RunPytest:$RunPytestB | Out-Host
} catch { Write-Host "[start] Pre-start maintenance error: $($_.Exception.Message)" }

# Build command line with per-process environment via cmd /c
# Resolve a unified SQLite EventLog path for all agents/tools
$eventsDb = Join-Path (Join-Path $repo 'var') 'events.db'
$envParts = @(
  'set ECOSYS_HEADLESS=' + ($(if ($HeadlessB) { '1' } else { '0' })),
  'set STOP_AFTER_SEC=' + $StopAfterSec,
  'set HEARTBEAT_SEC=' + $HeartbeatSec,
  'set HEALTH_SEC=' + $HealthSec,
  'set RESUMMARIZE_SEC=' + $ResummarizeSec,
  'set MEM_ROTATE_SEC=' + $MemRotateSec,
  'set ECOSYS_REPO_ROOT=' + $repo,
  'set ECOSYS_MEMORY_DB=' + $eventsDb,
  'set ASSISTANT_LOG_DIR=' + $logs,
  'set ECOSYS_ASSISTANT_LOG_DIR=' + $logs,
  'set ENABLE_JSONL_RECORDER=0',
  'set MEM_KEEP_LAST=2000',
  'set PYTHONUNBUFFERED=1',
  'set PYTHONIOENCODING=utf-8'
)
$joinedEnv = [string]::Join('&& ', $envParts)
# Use cmd.exe redirection for both modes
$cmdArgs = "/c $joinedEnv && `"$pyExe`" `"$repo\\main.py`" 1>> `"$stdout`" 2>> `"$stderr`""



Write-Host "[start] Repo: $repo"
Write-Host "[start] Python: $pyExe"
Write-Host "[start] Headless: $HeadlessB StopAfterSec: $StopAfterSec"

if ($BackgroundB) {
  $p = Start-Process -FilePath 'cmd.exe' -ArgumentList $cmdArgs -WorkingDirectory $repo -WindowStyle Hidden -PassThru
  $childPid = $p.Id
  Set-Content -Path $pidFile -Value $childPid
  Write-Host "[start] Launched background process PID $childPid"
  Write-Host "[start] Stdout: $stdout"
  Write-Host "[start] Stderr: $stderr"
} else {
  & cmd.exe $cmdArgs
}



