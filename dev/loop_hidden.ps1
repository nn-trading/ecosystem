$repo = Split-Path -Parent $PSScriptRoot
Start-Process -WindowStyle Hidden -FilePath (Join-Path $repo 'dev\run_loop.cmd')
