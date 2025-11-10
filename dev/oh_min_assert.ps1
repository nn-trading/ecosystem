param()
$ErrorActionPreference='SilentlyContinue'
$ROOT = (Split-Path -Parent $MyInvocation.MyCommand.Path); if (-not $ROOT) { $ROOT=(Convert-Path '.') }
$ok = @{}

$ok.OPENAI_KEY = Test-Path (Join-Path $ROOT 'api_key.txt')
$ok.TAIL = Test-Path (Join-Path $ROOT 'reports\chat\exact_tail.jsonl')
$ok.DB = Test-Path (Join-Path $ROOT 'var\events.db')
$startLog = Join-Path $ROOT 'logs\start_stdout.log'
$ok.LOGS = (Test-Path $startLog) -and ((Get-Content $startLog -ErrorAction SilentlyContinue -Tail 4000) -match 'inbox loop started|JobsWorker started|Ecosystem ready')

$py = Join-Path $ROOT '.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py='python' }
$testModel=$false
try {
  $k = Get-Content (Join-Path $ROOT 'api_key.txt') -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($k) { $testModel=$true }
} catch {}
$ok.OPENAI_READY = $testModel

$pass = ($ok.OPENAI_READY -and $ok.TAIL -and $ok.LOGS)
$summary = @{ pass=$pass; checks=$ok }
$summary | ConvertTo-Json | Set-Content -Encoding Ascii -LiteralPath (Join-Path $ROOT 'reports\MINIMUMS_ASSERT.json')
Write-Host ((Get-Content (Join-Path $ROOT 'reports\MINIMUMS_ASSERT.json')))
