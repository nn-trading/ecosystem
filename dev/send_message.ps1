param(
  [Parameter(Mandatory=$true)][string]$Prompt,
  [string]$System = 'You are a decisive desktop orchestrator. Keep answers short. When asked to act, propose concrete PowerShell commands for C:\bots\ecosys\tools\gui_tool.py or safe shell steps.'
)
$ErrorActionPreference='Continue'
if (-not $env:OPENAI_API_BASE -or -not $env:OPENAI_API_KEY) { Write-Host 'ERROR: Missing OPENAI_API_BASE/KEY (run use_gptoss.ps1 first)' -ForegroundColor Red; exit 1 }
$model = if ($env:OPENAI_MODEL) { $env:OPENAI_MODEL } else { 'openai/gpt-oss-20b' }

$body = @{
  model = $model
  messages = @(
    @{ role='system'; content=$System },
    @{ role='user'  ; content=$Prompt }
  )
  temperature = 0.2
} | ConvertTo-Json -Depth 8

$uri = ($env:OPENAI_API_BASE.TrimEnd('/') + '/chat/completions')
try {
  $resp = Invoke-RestMethod -Uri $uri -Headers @{ 'Authorization' = ('Bearer ' + $env:OPENAI_API_KEY) } -Method Post -Body $body -ContentType 'application/json'
} catch {
  Write-Host ('HTTP error: ' + $_.Exception.Message) -ForegroundColor Red
  exit 1
}

$rawPath = 'C:\bots\ecosys\reports\last_completion.json'
$resp | ConvertTo-Json -Depth 12 | Out-File $rawPath -Encoding utf8

$msg = $resp.choices[0].message.content
if (-not $msg) {
  try { $msg = ($resp.choices[0].delta.content) -join '' } catch {}
}
if (-not $msg) { $msg = '[no content]' }

$msg
Write-Host ('Saved raw -> ' + $rawPath) -ForegroundColor DarkGray
