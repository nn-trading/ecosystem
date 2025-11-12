$ErrorActionPreference="Stop"
$repo="C:\bots\ecosys"
Set-Location $repo
$reports = Join-Path $repo "reports\llm"
$newItemParams = @{ItemType="Directory"; Force=$true; Path=$reports}
New-Item @newItemParams | Out-Null

# --- Load OpenRouter key from secrets (one line, no quotes) ---
$keyPath = Join-Path $repo "secrets\openrouter.key"
if (-not (Test-Path $keyPath)) {
  Write-Host "OPENROUTER: MISSING secrets\openrouter.key"
  exit 0
}
$key = (Get-Content $keyPath -Raw).Trim()
if (-not $key) {
  Write-Host "OPENROUTER: EMPTY secrets\openrouter.key"
  exit 0
}

# --- Required headers per OpenRouter policy ---
$headers = @{
  "Authorization" = "Bearer $key"
  "Content-Type"  = "application/json"
  "HTTP-Referer"  = "https://github.com/nn-trading/ecosystem"
  "Referer"       = "https://github.com/nn-trading/ecosystem"
  "X-Title"       = "ecosys-autonomy"
}

# --- Minimal /chat/completions probe expecting exact marker ---
$body = @{
  model = "openai/gpt-4o-mini"
  messages = @(
    @{ role="system"; content="Return exactly the text I ask for." },
    @{ role="user";   content="ECOSYSTEM-LIVE-OPENROUTER" }
  )
} | ConvertTo-Json -Depth 6

$rawPath = Join-Path $reports "openrouter_probe_raw.txt"
$lastPath = Join-Path $reports "openrouter_probe.txt"
$ok = $false
try {
  $r = Invoke-WebRequest -Method Post -Uri "https://openrouter.ai/api/v1/chat/completions" -Headers $headers -Body $body -ErrorAction Stop
  $content = $r.Content
  $json = $null
  try { $json = $content | ConvertFrom-Json } catch {}
  if ($json -and $json.choices -and $json.choices[0].message.content -eq "ECOSYSTEM-LIVE-OPENROUTER") {
    "ECOSYSTEM-LIVE-OPENROUTER" | Out-File -Encoding UTF8 $lastPath
    $ok = $true
  } else {
    ("openrouter unexpected: " + ($json | ConvertTo-Json -Depth 8)) | Out-File -Encoding UTF8 $lastPath
  }
  $content | Out-File -Encoding UTF8 $rawPath
} catch {
  $errText = $_ | Out-String
  ("openrouter error: " + $errText.Trim()) | Out-File -Encoding UTF8 $lastPath
  $ok = $false
}

# --- If probe OK, switch provider to openrouter; else keep openai ---
$cfg = @()
if ($ok) {
  $cfg = @(
    "provider: openrouter",
    "model: openai/gpt-4o-mini"
  )
  Write-Host "OPENROUTER: OK -> switching provider to openrouter"
} else {
  $cfg = @(
    "provider: openai",
    "model: gpt-4o-mini"
  )
  Write-Host "OPENROUTER: still failing -> keeping provider=openai"
}
$cfg | Set-Content -Encoding UTF8 (Join-Path $repo "config\llm.yaml")

# --- Foreground smoke (non-blocking background loops off) ---
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Headless 1 -Background 0

# --- Print quick summary ---
$provider = (Get-Content .\config\llm.yaml | Where-Object {$_ -match '^provider:'}) -replace 'provider:\s*',''
Write-Host ("start.ps1: " + (Resolve-Path .\start.ps1))
Write-Host ("db: " + (Resolve-Path .\var\events.db))
Write-Host ("openai_probe: " + (Resolve-Path .\reports\llm\openai_probe.txt))
Write-Host ("openrouter_probe: " + (Resolve-Path .\reports\llm\openrouter_probe.txt))
Write-Host ("provider: " + $provider.Trim())
