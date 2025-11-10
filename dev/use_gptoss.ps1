$ErrorActionPreference='Continue'
$keyPath = 'C:\bots\ecosys\secrets\openrouter.key'
if(!(Test-Path $keyPath)){ Write-Host 'ERROR: missing C:\bots\ecosys\secrets\openrouter.key' -ForegroundColor Red; exit 1 }
$key = (Get-Content $keyPath -Raw).Trim()
if([string]::IsNullOrWhiteSpace($key)){ Write-Host 'ERROR: openrouter.key is empty' -ForegroundColor Red; exit 1 }

$env:OPENAI_API_BASE = 'https://openrouter.ai/api/v1'
$env:OPENAI_API_KEY  = $key
$env:OPENAI_MODEL    = 'openai/gpt-oss-20b'

Write-Host ('READY: GPT-OSS via OpenRouter') -ForegroundColor Green
Write-Host ('OPENAI_API_BASE=' + $env:OPENAI_API_BASE)
Write-Host ('OPENAI_MODEL=' + $env:OPENAI_MODEL)
