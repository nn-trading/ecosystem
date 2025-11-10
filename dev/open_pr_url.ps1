$ErrorActionPreference = 'Stop'
Set-Location 'C:\bots\ecosys'
$remote = git remote get-url origin
Write-Host ("origin url: {0}" -f $remote) -ForegroundColor Cyan
if ($remote -like 'git@github.com:*') {
  $parts = $remote -replace '^git@github.com:','' -replace '\.git$',''
  $web   = 'https://github.com/' + $parts
} elseif ($remote -like 'https://github.com/*') {
  $web   = $remote -replace '\.git$',''
} else {
  Write-Host 'ERROR: origin is not GitHub; cannot auto-build PR URL.' -ForegroundColor Red
  exit 1
}
$head = (git remote show origin | Select-String 'HEAD branch:') -replace '.*:\s*',''
$head = $head.Trim()
if ([string]::IsNullOrWhiteSpace($head)) { $head = 'main' }
$feature = 'feature/loggerdb-cli'
$url = "$web/compare/$head...$feature?expand=1"
Write-Host ("Opening PR URL: {0}" -f $url) -ForegroundColor Green
Start-Process $url
