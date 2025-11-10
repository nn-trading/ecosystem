$ErrorActionPreference = "Stop"
$keyPath = "C:\bots\ecosys\secrets\openrouter.key"
if(!(Test-Path $keyPath)){ Write-Host "ERROR: missing $keyPath" -ForegroundColor Red; exit 1 }
$key = (Get-Content $keyPath -Raw).Trim()
if([string]::IsNullOrWhiteSpace($key)){ Write-Host "ERROR: openrouter.key is empty" -ForegroundColor Red; exit 1 }

$env:OPENAI_API_BASE = "https://openrouter.ai/api/v1"
$env:OPENAI_API_KEY  = $key
$env:OPENAI_MODEL    = "openai/gpt-oss-20b"
$env:PYTHONUTF8      = "1"
$env:PYTHONIOENCODING= "utf-8"

$goal = "Open https://www.google.com/travel/flights?hl=en using openurl with {timeout: 8}. Then take a screenshot to C:\bots\ecosys\reports\screens\monitor0_proof.png (do not set monitor; default must be 0). Stop when done."
C:\bots\ecosys\.venv\Scripts\python.exe C:\bots\ecosys\brain_orchestrator.py --goal "$goal" --max_iters 3
