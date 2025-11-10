$ErrorActionPreference = 'Stop'
$root = 'C:\bots\ecosys'
$py   = Join-Path $root '.venv\Scripts\python.exe'

# 1) Download example.com -> reports\proofs\dl_example.html
& $py (Join-Path $root 'tools\file_tool.py') download --url 'https://example.com' --out (Join-Path $root 'reports\proofs\dl_example.html')

# 2) Notepad flow: open -> focus -> type -> hotkey ctrl+s -> wait -> press ESC -> close
& $py (Join-Path $root 'tools\app_tool.py')  open   --name 'notepad.exe'
Start-Sleep -Seconds 1
& $py (Join-Path $root 'tools\app_tool.py')  focus  --title 'Notepad'
& $py (Join-Path $root 'tools\gui_tool.py')  type   --text 'hotkey test' --enter
& $py (Join-Path $root 'tools\hotkey_tool.py') hotkey --combo 'ctrl+s' --interval 0.05
Start-Sleep -Seconds 1
& $py (Join-Path $root 'tools\hotkey_tool.py') press  --keys 'ESC'
& $py (Join-Path $root 'tools\app_tool.py')  close  --name 'notepad.exe'

Write-Host 'STEP 51 DONE' -ForegroundColor Green
