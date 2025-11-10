$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
$root = 'C:\bots\ecosys'
Set-Location -LiteralPath $root
if (!(Test-Path 'dev\__init__.py')) { '' | Set-Content -Encoding Ascii -LiteralPath 'dev\__init__.py' }
if (!(Test-Path 'configs')) { New-Item -ItemType Directory -Path 'configs' | Out-Null }
if (!(Test-Path 'configs\model.yaml')) { @('default: gpt-5','lock: true') | Set-Content -Encoding Ascii -LiteralPath 'configs\model.yaml' }
try { powershell -NoProfile -File '.\start.ps1' -Stop 1 | Out-Null } catch {}
powershell -NoProfile -File '.\start.ps1' -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2 | Out-Null
$py = '.\.venv\Scripts\python.exe'
if (!(Test-Path $py)) { $py = 'python' }
& $py -m dev.brain_chat_shell
