$ErrorActionPreference = 'Stop'
$p = 'C:\bots\ecosys\reports\ECOSYSTEM_READY.txt'
$screens = 'C:\bots\ecosys\reports\screens'
$shot = Join-Path $screens 'ecosystem_ready2.png'
$root = 'C:\bots\ecosys'

New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
Set-Content -Encoding UTF8 -Path $p -Value 'ECOSYSTEM READY'
if (!(Test-Path $p)) { Write-Error 'FAILED: file not written'; exit 1 }
Write-Host ("OK: wrote {0} ({1} bytes)" -f $p, (Get-Item $p).Length)

Set-Location $root
$logItem = Get-ChildItem 'reports\actions_*.json' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1

git add -f -- $p
if (Test-Path $shot) { git add -f -- $shot }
if ($null -ne $logItem) { git add -f -- $logItem.FullName }

$st = git status --porcelain
if ([string]::IsNullOrWhiteSpace($st)) {
  Write-Host 'Nothing to commit.'
} else {
  git commit -m 'chore(proof): add ECOSYSTEM_READY.txt + screenshot + actions log' -m 'Co-authored-by: openhands <openhands@all-hands.dev>'
  Write-Host 'Committed proof artifacts.' -ForegroundColor Green
}
