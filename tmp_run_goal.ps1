$ErrorActionPreference = 'Stop'
$repo = 'C:\bots\ecosys'
Set-Location $repo

# Load provider/model
$cfg = Get-Content .\config\llm.yaml -Raw
$prov = (($cfg -split "`n") | Where-Object { $_ -match '^provider:' }) -replace 'provider:\s*',''
$modl = (($cfg -split "`n") | Where-Object { $_ -match '^model:' }) -replace 'model:\s*',''
$prov = $prov.Trim()
$modl = $modl.Trim()

if ($prov -ieq 'openai') {
  if (-not $env:OPENAI_API_KEY -and (Test-Path .\secrets\openai.key)) {
    $env:OPENAI_API_KEY = (Get-Content .\secrets\openai.key -Raw).Trim()
  }
  $env:OPENAI_API_BASE = 'https://api.openai.com/v1'
  $env:OPENAI_MODEL    = $modl
}

$goal  = 'Open Notepad, type GPT5 OK, then take a desktop screenshot saved to C:\bots\ecosys\reports\screens\autonomy_gpt5_final.png and stop.'
$iters = 2

# Run goal; capture output to text (not JSON-parsed here to avoid quoting pitfalls)
$runOut = Join-Path $repo 'reports/last_run_output.txt'
& "$repo\dev\ecosys_goal.ps1" -Goal $goal -Iters $iters | Tee-Object -FilePath $runOut | Out-Host

# Locate the latest actions_*.json
$act = Get-ChildItem (Join-Path $repo 'reports') -Filter 'actions_*.json' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($act) {
  Write-Host "ACTIONS_LOG: $($act.FullName)"
  $content = Get-Content $act.FullName -Raw
  $hasModel = [bool]([regex]::Match($content, '"model"\s*:\s*"gpt-5"').Success)
  $hasVia   = [bool]([regex]::Match($content, '"via_responses"\s*:\s*true').Success)
  Write-Host "HAS_MODEL_GPT5: $hasModel"
  Write-Host "HAS_VIA_RESPONSES: $hasVia"
} else {
  Write-Host 'ACTIONS_LOG:'
  Write-Host 'HAS_MODEL_GPT5: False'
  Write-Host 'HAS_VIA_RESPONSES: False'
}

$ss = Join-Path $repo 'reports/screens/autonomy_gpt5_final.png'
Write-Host ("SCREENSHOT_EXISTS: " + (Test-Path $ss))

$dbg = Join-Path $repo 'reports/llm/responses_debug.jsonl'
Write-Host ("DEBUG_LOG_EXISTS: " + (Test-Path $dbg))
if (Test-Path $dbg) {
  Write-Host '--- DEBUG LOG TAIL ---'
  Get-Content $dbg -Tail 10 | Out-Host
}
