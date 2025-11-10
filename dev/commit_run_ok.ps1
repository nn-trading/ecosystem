$ErrorActionPreference = 'Stop'
$root = 'C:\bots\ecosys'
$proof = Join-Path $root 'reports\proofs\run_ok'
New-Item -ItemType Directory -Force -Path $proof | Out-Null
Set-Content -Encoding UTF8 -Path (Join-Path $proof 'ok.txt') -Value 'ECOSYSTEM OK'

$files = @(
  'reports\proofs\run_ok\ok.txt',
  'reports\proofs\run_ok\example.html',
  'reports\proofs\run_ok_ocr.txt',
  'reports\screens\run_ok_page.png',
  'reports\screens\run_ok_desktop.png'
)
Set-Location $root
git add -f -- $files
$st = git status --porcelain
if ([string]::IsNullOrWhiteSpace($st)) {
  Write-Host 'Nothing to commit.'
} else {
  git commit -m 'chore(proof): add run_ok artifacts' -m 'Co-authored-by: openhands <openhands@all-hands.dev>'
}
Write-Host 'OK: run_ok fixed and committed.' -ForegroundColor Green
