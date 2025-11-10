$ErrorActionPreference = "Stop"
$keyPath = "C:\bots\ecosys\secrets\openrouter.key"
$key = (Get-Content $keyPath -Raw).Trim()
$env:OPENAI_API_BASE = "https://openrouter.ai/api/v1"
$env:OPENAI_API_KEY  = $key
$env:OPENAI_MODEL    = "openai/gpt-oss-20b"
$env:PYTHONUTF8      = "1"
$env:PYTHONIOENCODING= "utf-8"

$goal = "Open https://www.google.com/travel/flights?hl=en and produce a Playwright page screenshot to C:\bots\ecosys\reports\screens\flights_page_shot.png using openurl with {page_shot: 'C:\\bots\\ecosys\\reports\\screens\\flights_page_shot.png', fullpage: true}. Stop when done."
C:\bots\ecosys\.venv\Scripts\python.exe C:\bots\ecosys\brain_orchestrator.py --goal "$goal" --max_iters 2
