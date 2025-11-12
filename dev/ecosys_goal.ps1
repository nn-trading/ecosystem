param(
  [Parameter(Mandatory=$true)][string]$Goal,
  [int]$Iters = 3
)
$ErrorActionPreference = "Stop"

# Load provider config and set env
$cfgPath = "C:\bots\ecosys\config\llm.yaml"
$provider = ""
$model = ""
if (Test-Path $cfgPath) {
  $yaml = Get-Content $cfgPath -Raw
  foreach ($m in [regex]::Matches($yaml, '(?m)^\s*([A-Za-z_]+)\s*:\s*(.+?)\s*$')) {
    $k = $m.Groups[1].Value.Trim()
    $v = $m.Groups[2].Value.Trim()
    if ($k -ieq 'provider') { $provider = $v }
    if ($k -ieq 'model')    { $model    = $v }
  }
}
if ([string]::IsNullOrWhiteSpace($provider)) { $provider = 'openrouter' }

if ($provider -ieq 'openai') {
  $keyPath = "C:\bots\ecosys\secrets\openai.key"
  $key = $null
  if (Test-Path $keyPath) { $key = (Get-Content $keyPath -Raw).Trim() }
  if ([string]::IsNullOrWhiteSpace($key)) { $key = $env:OPENAI_API_KEY }
  if ([string]::IsNullOrWhiteSpace($key)) { Write-Host "ERROR: Missing OpenAI API key. Put it in $keyPath or set OPENAI_API_KEY" -ForegroundColor Red; exit 1 }
  $env:OPENAI_API_BASE = "https://api.openai.com/v1"
  $env:OPENAI_API_KEY  = $key
  if ([string]::IsNullOrWhiteSpace($model)) { $model = "gpt-4o-mini" }
  $env:OPENAI_MODEL    = $model
}
else {
  # Default to OpenRouter
  $keyPath = "C:\bots\ecosys\secrets\openrouter.key"
  if(!(Test-Path $keyPath)){ Write-Host "ERROR: missing $keyPath" -ForegroundColor Red; exit 1 }
  $key = (Get-Content $keyPath -Raw).Trim()
  if([string]::IsNullOrWhiteSpace($key)){ Write-Host "ERROR: openrouter.key is empty" -ForegroundColor Red; exit 1 }
  $env:OPENAI_API_BASE = "https://openrouter.ai/api/v1"
  $env:OPENAI_API_KEY  = $key
  if ([string]::IsNullOrWhiteSpace($model)) { $model = "openai/gpt-oss-20b" }
  $env:OPENAI_MODEL    = $model
}

$env:PYTHONUTF8      = "1"
$env:PYTHONIOENCODING= "utf-8"

# Run
$py = "C:\bots\ecosys\.venv\Scripts\python.exe"
$g = $Goal -replace "`r`n",' ' -replace "`n",' ' -replace "`r",' '
$env:GOAL_TEXT = $g
$argsList = @("C:\bots\ecosys\brain_orchestrator.py", "--goal", "__ENV__", "--max_iters", "$Iters")
& $py @argsList
