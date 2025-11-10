$ErrorActionPreference='Stop'
$root='C:\bots\ecosys'
$py=Join-Path $root '.venv\Scripts\python.exe'
if(!(Test-Path $py)){
  try { py -3 -m venv (Join-Path $root '.venv') } catch { python -m venv (Join-Path $root '.venv') }
  $py=Join-Path $root '.venv\Scripts\python.exe'
}
& $py -m pip install -U pip
& $py -m pip install --upgrade --quiet 'openai>=1,<2' pyautogui pywin32 mss pillow screeninfo keyboard requests psutil
& $py -m dev.gauntlet_e2e
$e2e=Join-Path $root 'dev\oh_end2end.ps1'
if(Test-Path $e2e){ powershell -NoProfile -ExecutionPolicy Bypass -File $e2e }
