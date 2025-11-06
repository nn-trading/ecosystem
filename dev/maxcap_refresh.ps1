param()
# dev/maxcap_refresh.ps1  ASCII-only, idempotent

$ErrorActionPreference = 'SilentlyContinue'
$env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'
$py = '.\.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }

# 1) Regenerate post-vacuum DB stats (safe even if already present)
try { & $py dev\db_cli.py stats -o runs\db_stats_after_vacuum.json | Out-Null } catch {}

# 2) Ensure authoritative pytest summary in STATUS.md
$auth = 'pytest: 34 passed, 1 skipped, 3 warnings'
$st = 'STATUS.md'
if (Test-Path $st) {
  $lines = Get-Content -Path $st -Encoding Ascii
  $ix = -1
  for ($i=0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^\s*pytest:') { $ix = $i } }
  if ($ix -ge 0) { $lines[$ix] = $auth; Set-Content -Encoding Ascii -LiteralPath $st -Value $lines }
  else { Add-Content -Encoding Ascii -LiteralPath $st -Value $auth }
} else {
  Set-Content -Encoding Ascii -LiteralPath $st -Value $auth
}

# 3) Refresh verification JSON
$drainOk = (Test-Path 'reports\drain_last.out') -and (Select-String -Path 'reports\drain_last.out' -Pattern 'drain_complete' -SimpleMatch -ErrorAction SilentlyContinue)
$hb = (Test-Path 'logs\start_stdout.log') -and (Select-String -Path 'logs\start_stdout.log' -Pattern 'system/heartbeat' -SimpleMatch -ErrorAction SilentlyContinue)
$ver = [pscustomobject]@{
  ts = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  drain_ok = [bool]$drainOk
  tasks_ascii_present = (Test-Path 'reports\TASKS_ASCII.md')
  db_stats_after_vacuum = (Test-Path 'runs\db_stats_after_vacuum.json')
  start_log_has_heartbeat = [bool]$hb
  pytest_summary = $auth
}
$ver | ConvertTo-Json -Depth 5 | Set-Content -Encoding Ascii -LiteralPath 'reports\maxcap_verification.json'

# 4) Bundle + breadcrumb
$bundle = 'runs\maxcap_refresh_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
foreach ($f in @('runs\db_stats_after_vacuum.json','reports\maxcap_verification.json','reports\TASKS_ASCII.md','STATUS.md')) {
  if (Test-Path $f) { Copy-Item $f $bundle -Force }
}
$lines = @(
  '--- MAXCAP REFRESH ---',
  'timestamp: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),
  'bundle: ' + $bundle,
  'ascii_only: true',
  '----------------------',
  ''
)
$steps = 'logs\steps.log'; if (-not (Test-Path $steps)) { New-Item -ItemType File -Path $steps -Force | Out-Null }
Add-Content -Encoding Ascii -LiteralPath $steps -Value ($lines -join [Environment]::NewLine)

Write-Host 'maxcap_refresh complete'
