$ErrorActionPreference='Stop'
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT
if (!(Test-Path 'dev\__init__.py')){''|Set-Content -Encoding Ascii -LiteralPath 'dev\__init__.py'}
if (!(Test-Path 'configs')){New-Item -ItemType Directory -Path 'configs' | Out-Null}
Set-Content -Encoding Ascii -LiteralPath 'configs\model.yaml' -Value "default: gpt-5`nlock: true"
& (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null
& (Join-Path $ROOT 'start.ps1') -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
$py = Join-Path $ROOT '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py='python' }
if (Test-Path 'dev\brain_chat_shell.py') { Start-Process $py -ArgumentList '-m','dev.brain_chat_shell' } elseif (Test-Path 'dev\chat_shell.py') { Start-Process $py -ArgumentList 'dev\chat_shell.py' } else { Start-Process $py -ArgumentList '-m','dev.chat_shell' }
