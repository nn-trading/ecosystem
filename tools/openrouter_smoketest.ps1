$ErrorActionPreference = 'Stop'
$KeyPath = 'C:\bots\ecosys\secrets\openrouter.key'
if (-not (Test-Path $KeyPath)) { throw "Key file not found: $KeyPath" }
$OR = Get-Content -Path $KeyPath -Raw
$OR = $OR.Trim()
$env:OPENAI_API_BASE = 'https://openrouter.ai/api/v1'
$env:OPENAI_API_KEY = $OR
$env:OPENAI_MODEL = 'openai/gpt-oss-20b'
$body = @{ model=$env:OPENAI_MODEL; messages=@(@{role='user';content='Reply with: OK'}) } | ConvertTo-Json -Depth 5
$headers = @{ Authorization = "Bearer $($env:OPENAI_API_KEY)"; 'Content-Type'='application/json' }
$dest = 'C:\bots\ecosys\reports\gptoss_smoketest.json'
try {
  $resp = Invoke-RestMethod -Method Post -Uri ($env:OPENAI_API_BASE + '/chat/completions') -Headers $headers -ContentType 'application/json' -Body $body
  $resp | ConvertTo-Json -Depth 10 | Out-File $dest -Encoding utf8
  Write-Host "OpenRouter smoketest written: $dest" -ForegroundColor Green
} catch {
  Write-Host 'OpenRouter smoke FAIL' -ForegroundColor Red
  $_ | Out-String | Out-File $dest -Encoding utf8
  exit 1
}
