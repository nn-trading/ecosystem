Set-StrictMode -Version 2
$ErrorActionPreference='Stop'
Set-Location -LiteralPath 'C:\bots\ecosys'
New-Item -ItemType Directory -Force -Path config | Out-Null
New-Item -ItemType Directory -Force -Path configs | Out-Null
New-Item -ItemType Directory -Force -Path reports | Out-Null
New-Item -ItemType Directory -Force -Path reports\chat | Out-Null
New-Item -ItemType Directory -Force -Path logs | Out-Null
Set-Content -Encoding Ascii -LiteralPath config\model.yaml -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath configs\model.yaml -Value "default: gpt-5`nlock: true"
Set-Content -Encoding Ascii -LiteralPath config\comms.yaml -Value "mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl"
Set-Content -Encoding Ascii -LiteralPath configs\comms.yaml -Value "mode: brain`necho: false`ntail: reports/chat/exact_tail.jsonl"
if (Test-Path TASKS.md) { $t=Get-Content -Raw -Encoding UTF8 TASKS.md; $t=$t -replace '[^\u0000-\u007F]',''; Set-Content -Encoding Ascii TASKS.md $t }
if (Test-Path STATUS.md) { $t=Get-Content -Raw -Encoding UTF8 STATUS.md; $t=$t -replace '[^\u0000-\u007F]',''; Set-Content -Encoding Ascii STATUS.md $t }
New-Item -ItemType File -Force -Path reports\chat\exact_tail.jsonl | Out-Null
powershell -NoProfile -File start.ps1 -Stop 1
powershell -NoProfile -File start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 1 -RunPytest 0 -DoMaintain 0 -HeartbeatSec 2 -HealthSec 2
Add-Content -Encoding Ascii logs\steps.log "[ASCII-01] applied at $(Get-Date -Format s)"
