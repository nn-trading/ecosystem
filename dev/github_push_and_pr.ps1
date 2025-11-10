param(
  [string]$Org = 'YOUR_GITHUB_ORG',
  [string]$Repo = 'YOUR_REPO',
  [string]$Branch = 'feature/loggerdb-cli',
  [string]$Token = '',
  [switch]$Open
)
$ErrorActionPreference = 'Stop'
Set-Location 'C:\bots\ecosys'

if (git remote | Select-String '^github$' -Quiet) {
  git remote remove github | Out-Null
}
$remoteUrl = "https://github.com/$Org/$Repo.git"
if (-not [string]::IsNullOrWhiteSpace($Token)) {
  $authUrl = "https://$Token@github.com/$Org/$Repo.git"
} else {
  $authUrl = $remoteUrl
}
Write-Host ("Adding remote 'github': {0}" -f $authUrl) -ForegroundColor Cyan

# Add remote (idempotent remove+add above)
git remote add github $authUrl | Out-Null

# Try push; don't fail script if push fails
$pushOk = $true
& git push -u github $Branch
$ec = $LASTEXITCODE
if ($ec -ne 0) {
  $pushOk = $false
  Write-Warning ("git push failed with exit code {0}" -f $ec)
}

# Determine HEAD branch for compare URL
$head = 'main'
$headLine = & git remote show github | Select-String 'HEAD branch:'
if ($headLine) {
  $head = ($headLine -replace '.*:\s*','').Trim()
}

$url = 'https://github.com/{0}/{1}/compare/{2}...{3}?expand=1' -f $Org,$Repo,$head,$Branch
Write-Host ("PR URL: {0}" -f $url) -ForegroundColor Green
if ($Open) { Start-Process $url }

# Restore remote to tokenless URL if token was used
if ($authUrl -ne $remoteUrl) {
  git remote set-url github $remoteUrl | Out-Null
}

Write-Host ("Done. Remote={0}, push_ok={1}" -f $remoteUrl, $pushOk) -ForegroundColor Magenta
exit 0
