# C:\bots\ecosys\dev\find_and_start_chat.ps1  (PS5-compatible; prompts for --goal if orchestrator)
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding=[Text.Encoding]::UTF8; [Console]::InputEncoding=[Text.Encoding]::UTF8 } catch {}
Set-Location 'C:\bots\ecosys'

$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:ECOSYS_AUTOPROBE='0'

# Optional OpenRouter env
if (Test-Path '.\dev\use_gptoss.ps1') { . .\dev\use_gptoss.ps1 }

# Resolve Python
$py = 'C:\bots\ecosys\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  try { $py = (& py -3 -c 'import sys; print(sys.executable)') } catch {}
  if (-not $py) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source } else { $py = $null }
  }
}

# Find entrypoint
$entries = @(
  'brain_orchestrator.py',
  'chat\brain_chat.py',
  'brain_chat.py',
  'agent.py',
  'ecosys.py',
  'main.py',
  'start.py',
  'app.py'
)
$found = $null
foreach ($e in $entries) { if (Test-Path $e) { $found = $e; break } }

# Logs
$logDir = '.\reports\logs'
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$launchLog = Join-Path $logDir 'brain_chat_launch.log'
Add-Content -Path $launchLog -Value ('--- ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ---')
Add-Content -Path $launchLog -Value ('PWD: ' + (Get-Location))

$pyStr = if ($py) { $py } else { '<not found>' }
$foundStr = if ($found) { $found } else { '<not found>' }
Add-Content -Path $launchLog -Value ('Python: ' + $pyStr)
Add-Content -Path $launchLog -Value ('Entrypoint: ' + $foundStr)

if (-not $py) {
  Write-Host 'ERROR: Python not found (.venv, py, or python on PATH).' -ForegroundColor Red
  Write-Host ('See ' + $launchLog); Read-Host 'Press Enter to close'; exit 1
}
if (-not $found) {
  Write-Host 'ERROR: No entrypoint found (brain_orchestrator.py/agent.py/etc.).' -ForegroundColor Red
  Write-Host ('See ' + $launchLog); Read-Host 'Press Enter to close'; exit 1
}

# If orchestrator, prompt for a goal and pass it
if ([System.IO.Path]::GetFileName($found) -eq 'brain_orchestrator.py') {
  Write-Host ('Launching Brain Orchestrator -> ' + $found) -ForegroundColor Green
  $goal = Read-Host 'Enter goal for --goal (blank to cancel)'
  if ([string]::IsNullOrWhiteSpace($goal)) { Write-Host 'No goal provided. Exiting.' -ForegroundColor Yellow; Read-Host 'Press Enter to close'; exit 0 }
  $iters = Read-Host 'Max iters (default 3)'
  if (-not ($iters -as [int])) { $iters = 3 }
  & $py -u $found --goal $goal --max_iters $iters
} else {
  Write-Host ('Launching -> ' + $found) -ForegroundColor Green
  & $py -u $found
}
Write-Host 'Chat exited.' -ForegroundColor Yellow
Read-Host 'Press Enter to close'
