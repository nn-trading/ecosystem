param(
  [int]$STOP_AFTER_SEC = 60,
  [int]$HEARTBEAT_SEC = 1,
  [int]$HEALTH_SEC = 5,
  [int]$KEEP_LAST = 50000,
  [int]$PROBE_TAIL = 500
)
$ErrorActionPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $repo "logs"
$transDir = Join-Path $logs "transcripts"
$probeDir = Join-Path $logs "probes"
New-Item -ItemType Directory -Force -Path $logs,$transDir,$probeDir | Out-Null
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$transcript = Join-Path $transDir "resume_$ts.txt"
Start-Transcript -Path $transcript -Force | Out-Null

Write-Host "[1/5] Kill stale probe/rotate processes..."
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'probe_events\.py|quick_probe\.py|rotate_events\.py|fast_rotate\.py' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }

Write-Host "[2/5] Start headless for $STOP_AFTER_SEC s..."
& "$repo\dev\start_headless.ps1" -STOP_AFTER_SEC $STOP_AFTER_SEC -HEARTBEAT_SEC $HEARTBEAT_SEC -HEALTH_SEC $HEALTH_SEC

Write-Host "[3/5] Rotate events to last $KEEP_LAST lines..."
$env:KEEP_LAST = "$KEEP_LAST"
$rotateOut = & python "$repo\dev\fast_rotate.py"
$rotateOut | Write-Host

Write-Host "[4/5] Probe last $PROBE_TAIL events..."
$env:PROBE_TAIL = "$PROBE_TAIL"
$probeOut = & python "$repo\dev\quick_probe.py"
$probeOut | Write-Host
$probePath = Join-Path $probeDir "probe_$ts.json"
$probeOut | Out-File -FilePath $probePath -Encoding UTF8

Write-Host "[5/5] Commit locally (no push)..."
git -C "$repo" config --get user.name >$null 2>&1; if ($LASTEXITCODE -ne 0) { git -C "$repo" config user.name "openhands" }
git -C "$repo" config --get user.email >$null 2>&1; if ($LASTEXITCODE -ne 0) { git -C "$repo" config user.email "openhands@all-hands.dev" }
git -C "$repo" add -A
git -C "$repo" commit -m "ops: resume_run.ps1 with transcript; probe snapshots; rotate+probe hardened" -m "Co-authored-by: openhands <openhands@all-hands.dev>"
if ($LASTEXITCODE -ne 0) { Write-Host "No changes to commit." }

Stop-Transcript | Out-Null
Write-Host "Transcript: $transcript"
Write-Host "Probe snapshot: $probePath"
exit 0
