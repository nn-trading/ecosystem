# C:\bots\ecosys\dev\ecosys_boot.ps1
$ErrorActionPreference='Continue'
try { [Console]::OutputEncoding=[Text.Encoding]::UTF8; [Console]::InputEncoding=[Text.Encoding]::UTF8 } catch {}
Set-Location 'C:\bots\ecosys'

# Ensure dirs
foreach($d in '.\dev','.\reports','.\reports\screens'){ if(!(Test-Path $d)){ New-Item -ItemType Directory -Force -Path $d | Out-Null } }

# Kill stale helper windows
try {
  Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match 'console_reply\.ps1' -or
    $_.CommandLine -match 'ecosys_front\.ps1' -or
    $_.CommandLine -match 'find_and_start_chat\.ps1'
  } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}

# Session env
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'

# Launch viewer
if (Test-Path '.\dev\console_reply.ps1') {
  Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File','.\\dev\\console_reply.ps1' | Out-Null
}

# Launch front chat
if (Test-Path '.\dev\ecosys_front.ps1') {
  Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File','.\\dev\\ecosys_front.ps1' | Out-Null
}

# Optionally Brain Chat
if (Test-Path '.\dev\find_and_start_chat.ps1') {
  Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File','.\\dev\\find_and_start_chat.ps1' | Out-Null
}

Write-Host 'Ecosystem boot: viewer + front chat (and brain chat if present) launched.' -ForegroundColor Green
