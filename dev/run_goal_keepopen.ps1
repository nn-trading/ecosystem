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

$goal = "Open https://www.google.com/travel/flights?hl=en and keep it visible using openurl with {timeout: 10} (or {keep_open: true}). Do NOT use shell for waiting; if extra delay is needed, use wait {seconds: 2}. Then take a screenshot to C:\bots\ecosys\reports\screens\keepopen_proof.png. Stop when done."

C:\bots\ecosys\.venv\Scripts\python.exe C:\bots\ecosys\brain_orchestrator.py --goal "$goal" --max_iters 3
