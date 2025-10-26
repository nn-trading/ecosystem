$path = 'C:\bots\ecosys\start.ps1'
$raw = Get-Content -Raw -Path $path
$pattern = '(?ms)^# Use cmd\.exe redirection.*?(?=\r?\n\s*Write-Host \[start\] Repo:)'
$replacement = "# Use cmd.exe redirection when backgrounding; in foreground, use the same args string`r`n" +
'$cmdArgs = "/c $joinedEnv && `"$pyExe`" `"$repo\\main.py`" 1>> `"$stdout`" 2>> `"$stderr`""' + "`r`n"
$raw2 = [regex]::Replace($raw, $pattern, $replacement)
Set-Content -Path $path -Value $raw2 -Encoding UTF8
