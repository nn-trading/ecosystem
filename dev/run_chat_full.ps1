param()
$ErrorActionPreference='Stop'
$DEV=$PSScriptRoot; $ROOT=(Get-Item $DEV).Parent.FullName
Set-Location -LiteralPath $ROOT
$py = Join-Path $ROOT '.venv\Scripts\python.exe'; if (!(Test-Path -LiteralPath $py)) { $py='python' }
$env:MODEL_NAME='gpt-5'; $env:AGENT_DANGER_MODE='1'; $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null
powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
& $py -m dev.brain_chat_shell
