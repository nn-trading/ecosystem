param(
  [Parameter(Mandatory=$true)][string]$Goal,
  [int]$Iters = 3
)
$ErrorActionPreference = "Stop"

# Load GPT-OSS (OpenRouter) key
$keyPath = "C:\bots\ecosys\secrets\openrouter.key"
if(!(Test-Path $keyPath)){ Write-Host "ERROR: missing $keyPath" -ForegroundColor Red; exit 1 }
$key = (Get-Content $keyPath -Raw).Trim()
if([string]::IsNullOrWhiteSpace($key)){ Write-Host "ERROR: openrouter.key is empty" -ForegroundColor Red; exit 1 }

# Env for orchestrator
$env:OPENAI_API_BASE = "https://openrouter.ai/api/v1"
$env:OPENAI_API_KEY  = $key
$env:OPENAI_MODEL    = "openai/gpt-oss-20b"
$env:PYTHONUTF8      = "1"
$env:PYTHONIOENCODING= "utf-8"

# Run
$py = "C:\bots\ecosys\.venv\Scripts\python.exe"
& $py "C:\bots\ecosys\brain_orchestrator.py" --goal $Goal --max_iters $Iters
