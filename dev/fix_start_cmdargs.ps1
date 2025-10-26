$path = 'C:\bots\ecosys\start.ps1'
$raw = Get-Content -Raw -Path $path
# Remove any existing $cmdArgs assignment lines
$raw2 = [regex]::Replace($raw, '(?m)^\s*\$cmdArgs\s*=.*\r?\n', '')
# Build insert block
$insert = "# Use cmd.exe redirection for both modes`r`n" + '$cmdArgs = "/c $joinedEnv && `"$pyExe`" `"$repo\\main.py`" 1>> `"$stdout`" 2>> `"$stderr`""' + "`r`n"
# Insert after $joinedEnv line
$raw3 = [regex]::Replace($raw2, '(?m)(^\$joinedEnv\s*=\s*\[string\]::Join\(''&& '',\s*\$envParts\)\s*\r?\n)', { param($m) $m.Value + $insert })
Set-Content -Path $path -Value $raw3 -Encoding UTF8
