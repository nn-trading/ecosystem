$ErrorActionPreference='Continue'
Set-Location 'C:\bots\ecosys'
Start-Process powershell -ArgumentList ""-NoProfile -ExecutionPolicy Bypass -NoExit -File "C:\bots\ecosys\dev\console_reply.ps1""" | Out-Null
Start-Process powershell -ArgumentList ""-NoProfile -ExecutionPolicy Bypass -NoExit -File "C:\bots\ecosys\dev\find_and_start_chat.ps1"""   | Out-Null
Write-Host 'Ecosystem boot launched: viewer + brain chat (NoExit).' -ForegroundColor Green
