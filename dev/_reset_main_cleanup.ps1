$ErrorActionPreference = 'Stop'
Set-Location 'C:\bots\ecosys'

# Fetch from 'github'
git fetch github

# Ensure we are on local 'main' that tracks github/main
$localMain = git branch --list main
if (-not $localMain) {
  git checkout -b main github/main
} else {
  git checkout main
}

# Reset local main to remote
git reset --hard github/main

# Delete feature branch if it exists
$feat = git branch --list 'feature/loggerdb-cli'
if ($feat) {
  git branch -D 'feature/loggerdb-cli'
}

# Unset hooks path (ignore errors)
try { git config --unset core.hooksPath } catch {}

git status -sb
Write-Host 'OK: main reset to github/main; feature/loggerdb-cli deleted; core.hooksPath unset.' -ForegroundColor Green
