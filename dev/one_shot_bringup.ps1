param()
$ErrorActionPreference = 'Continue'

# Discover repo and output roots dynamically
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $scriptDir
if (-not (Test-Path $repo)) { $repo = (Get-Location).Path }
$outRoot = Split-Path -Parent $repo
if (-not (Test-Path $outRoot)) { $outRoot = $repo }

$reportsDir   = Join-Path $outRoot 'reports'
$outDir       = Join-Path $outRoot 'out'
$artifactsDir = Join-Path $outRoot 'artifacts'

New-Item -ItemType Directory -Force -Path $reportsDir, $outDir, $artifactsDir | Out-Null

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$bringupLog = Join-Path $reportsDir ("bringup_" + $ts + ".log")

function W([string]$msg) {
  $line = "[{0}] {1}" -f ((Get-Date).ToString('o')), $msg
  $line | Tee-Object -FilePath $bringupLog -Append | Out-Host
}

W "[begin] repo=$repo outRoot=$outRoot"

# 1) Stop any background instance
try {
  W "Stopping background via start.ps1 -Stop"
  & (Join-Path $repo 'start.ps1') -Stop 1 2>&1 | Tee-Object -FilePath $bringupLog -Append | Out-Host
} catch { W ("stop error: " + $_.Exception.Message) }

# 2) Ensure venv and dependencies with a short headless run
try {
  W "Ensuring venv/deps via start.ps1 short run"
  & (Join-Path $repo 'start.ps1') -Headless 1 -Background 0 -EnsureVenv 1 -EnsureDeps 1 -StopAfterSec 2 -HeartbeatSec 1 -HealthSec 2 -RunPytest 0 2>&1 |
    Tee-Object -FilePath $bringupLog -Append | Out-Host
} catch { W ("deps ensure error: " + $_.Exception.Message) }

# 3) Foreground headless smoke to generate events
try {
  W "Running foreground headless smoke (StopAfterSec=10)"
  & (Join-Path $repo 'start.ps1') -Headless 1 -Background 0 -EnsureVenv 1 -EnsureDeps 0 -StopAfterSec 10 -HeartbeatSec 1 -HealthSec 2 2>&1 |
    Tee-Object -FilePath $bringupLog -Append | Out-Host
} catch { W ("smoke error: " + $_.Exception.Message) }

# 4) Run pytest and capture output
$py = Join-Path $repo '.venv/ Scripts/python.exe'
$py = $py -replace ' ', ''
if (-not (Test-Path $py)) {
  try { $py = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Source } catch {}
  if (-not $py) { $py = 'python' }
}
$varDir = Join-Path $repo 'var'
New-Item -ItemType Directory -Force -Path $varDir | Out-Null
$pytestOut = Join-Path $varDir 'pytest_output.txt'
try {
  W "Running pytest -q"
  & $py -m pytest -q 2>&1 | Tee-Object -FilePath $pytestOut -Append | Tee-Object -FilePath $bringupLog -Append | Out-Host
} catch { W ("pytest error: " + $_.Exception.Message) }

# 5) Inventory repository (path | size | sha256)
try {
  $inv = Join-Path $reportsDir ("inventory_" + $ts + ".txt")
  "Inventory for $repo at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -Path $inv -Encoding ascii
  'Requirements:' | Add-Content -Path $inv -Encoding ascii
  $req = Join-Path $repo 'requirements.txt'
  if (Test-Path $req) { Get-Content $req | ForEach-Object { $_ } | Add-Content -Path $inv -Encoding ascii } else { 'requirements.txt missing' | Add-Content -Path $inv -Encoding ascii }
  'Files (name | size | sha256):' | Add-Content -Path $inv -Encoding ascii
  Get-ChildItem $repo -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
    try {
      $h = Get-FileHash -Algorithm SHA256 -Path $_.FullName -ErrorAction Stop
      ('{0} | {1} | {2}' -f $_.FullName, $_.Length, $h.Hash) | Add-Content -Path $inv -Encoding ascii
    } catch {
      ('ERR: ' + $_.FullName + ' - ' + $_.Exception.Message) | Add-Content -Path $inv -Encoding ascii
    }
  }
  'Done.' | Add-Content -Path $inv -Encoding ascii
  W ("[inventory] Wrote " + $inv)
} catch { W ("inventory error: " + $_.Exception.Message) }

# 6) Copy key artifacts/logs
try {
  $stdout = Join-Path $repo 'logs/start_stdout.log'
  $stderr = Join-Path $repo 'logs/start_stderr.log'
  if (Test-Path $stdout) { Copy-Item -Path $stdout -Destination (Join-Path $outDir ("start_stdout_" + $ts + ".log")) -Force }
  if (Test-Path $stderr) { Copy-Item -Path $stderr -Destination (Join-Path $outDir ("start_stderr_" + $ts + ".log")) -Force }
  $eval = Join-Path $repo 'var/eval_results.jsonl'
  if (Test-Path $eval) { Copy-Item -Path $eval -Destination (Join-Path $reportsDir ("eval_results_" + $ts + ".jsonl")) -Force }
  $eventsDb = Join-Path $repo 'var/events.db'
  if (Test-Path $eventsDb) { Copy-Item -Path $eventsDb -Destination (Join-Path $artifactsDir ("events_" + $ts + ".db")) -Force }
  W "Copied artifacts to out/reports/artifacts"
} catch { W ("artifact copy error: " + $_.Exception.Message) }

# 7) Generate concise run summary report
try {
  $summary = Join-Path $reportsDir ("run_summary_" + $ts + ".txt")
  $lines = @()
  $lines += "Run timestamp: $ts"
  $lines += "Repo: $repo"
  if (Test-Path $pytestOut) {
    try {
      $passLine = (Select-String -Path $pytestOut -Pattern 'passed|failed|error|warnings' | Select-Object -Last 1).Line
      if ($passLine) { $lines += ("Pytest: " + ($passLine -replace '[^\x20-\x7E]', '')) }
    } catch {}
  }
  $lines += "Smoke: executed headless foreground run (StopAfterSec=10)"
  $lines += "Logs: see bringup log and start logs"
  $lines | Set-Content -Path $summary -Encoding ascii
  W ("[summary] Wrote " + $summary)
} catch { W ("summary error: " + $_.Exception.Message) }

# 8) Update STATUS.md with latest run
try {
  $statusPath = Join-Path $repo 'STATUS.md'
  $append = @()
  $append += ""
  $append += "Recent run: $ts"
  if (Test-Path $pytestOut) {
    try {
      $passLine = (Select-String -Path $pytestOut -Pattern 'passed|failed|error|warnings' | Select-Object -Last 1).Line
      if ($passLine) { $append += ("Pytest: " + ($passLine -replace '[^\x20-\x7E]', '')) }
    } catch {}
  }
  $append += "Smoke: headless foreground run completed"
  $append += "Artifacts: reports and out under $outRoot"
  $append | Add-Content -Path $statusPath -Encoding ascii
  W "Updated STATUS.md"
} catch { W ("STATUS update error: " + $_.Exception.Message) }

W "[end] bring-up complete"
