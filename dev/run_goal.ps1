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

C:\bots\ecosys\.venv\Scripts\python.exe C:\bots\ecosys\brain_orchestrator.py --goal 'Create the folder C:\bots\ecosys\reports\proofs if it does not exist (use shell). Then open https://www.google.com/travel/flights?hl=en and keep it open for 10 seconds. Then take a screenshot to C:\bots\ecosys\reports\screens\proof_shell_gui.png. Stop when done.' --max_iters 3
