$ErrorActionPreference = 'Stop'
$lnk = Join-Path $env:USERPROFILE 'Desktop\Ecosystem Front Chat.lnk'
$ws  = New-Object -ComObject WScript.Shell
$s   = $ws.CreateShortcut($lnk)
$s.TargetPath       = 'powershell.exe'
$s.Arguments        = "-NoProfile -ExecutionPolicy Bypass -File `"C:\bots\ecosys\dev\ecosys_front.ps1`""
$s.WorkingDirectory = 'C:\bots\ecosys\dev'
$s.IconLocation     = 'powershell.exe,0'
$s.Description      = 'Type goals; the Ecosystem executes them'
$s.Save()
Write-Host ("OK: created shortcut -> " + $lnk) -ForegroundColor Green
