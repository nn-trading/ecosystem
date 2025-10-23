$ErrorActionPreference = 'SilentlyContinue'
$env:ECOSYS_HEADLESS = '1'
if (-not $env:STOP_AFTER_SEC) { $env:STOP_AFTER_SEC = '10' }
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$stdout = Join-Path $logs 'headless_stdout.log'
$stderr = Join-Path $logs 'headless_stderr.log'
$p = Start-Process -FilePath python -ArgumentList 'main.py' -WorkingDirectory $root -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$p.Id | Set-Content -Path (Join-Path $logs 'headless_pid.txt')
