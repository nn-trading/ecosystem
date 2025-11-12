$ErrorActionPreference="Stop"
$repo="C:\bots\ecosys"
Set-Location $repo

# Try to automerge feature/docs-health -> main if token exists
$tokFile = Join-Path $repo "secrets\github_token.txt"
$haveTok = Test-Path $tokFile
if ($haveTok) {
  $env:GITHUB_TOKEN = (Get-Content $tokFile).Trim()
}

# Ensure branch exists locally
git fetch github
if (-not (git rev-parse --verify feature/docs-health 2>$null)) { git switch -c feature/docs-health --track github/feature/docs-health } else { git switch feature/docs-health }

# Attempt PR create+merge when token present
$prUrl = ""
if ($haveTok) {
  $owner="nn-trading"; $repoName="ecosystem"
  $title="docs(health): add health report + counts + README"
  $body="Adds scripts\health_report.ps1 and dev\health_counts.py, README usage, and unifies scheduled task naming."
  $pr = Invoke-RestMethod -Method Post -Uri "https://api.github.com/repos/$owner/$repoName/pulls" -Headers @{Authorization="Bearer $env:GITHUB_TOKEN"; "User-Agent"="ecosys"} -Body (@{title=$title; head="feature/docs-health"; base="main"; body=$body} | ConvertTo-Json)
  $prUrl = $pr.html_url
  # merge
  Invoke-RestMethod -Method Put -Uri "https://api.github.com/repos/$owner/$repoName/pulls/$($pr.number)/merge" -Headers @{Authorization="Bearer $env:GITHUB_TOKEN"; "User-Agent"="ecosys"} -Body (@{merge_method="squash"} | ConvertTo-Json) | Out-Null
  Write-Host ("PR_MERGED: " + $prUrl)
} else {
  $cmp="https://github.com/nn-trading/ecosystem/compare/main...feature/docs-health?expand=1"
  Write-Host ("PR_COMPARE: " + $cmp)
}

# Sync local main to remote main and delete branch (best-effort)
git fetch github
git switch main
git reset --hard github/main
git branch -D feature/docs-health 2>$null | Out-Null
git push github :feature/docs-health 2>$null | Out-Null

# Run a fresh health report
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\health_report.ps1
