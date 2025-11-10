$ErrorActionPreference = 'Stop'
$branch     = 'feature/loggerdb-cli'
$repoRoot   = 'C:\bots\ecosys'
$remoteName = 'github'
$remoteUrl  = 'https://github.com/nn-trading/ecosystem.git'
$co         = 'Co-authored-by: openhands <openhands@all-hands.dev>'

Set-Location $repoRoot

# Ensure we are on target branch
$cur = (git rev-parse --abbrev-ref HEAD).Trim()
if ($cur -ne $branch) { git checkout $branch }

# Ensure git identity
if (-not (git config user.name))  { git config user.name  'openhands' }
if (-not (git config user.email)) { git config user.email 'openhands@all-hands.dev' }

# Update .gitignore to ignore logs/
$updated = $false
if (-not (Test-Path '.gitignore')) {
  Set-Content -Encoding UTF8 -Path '.gitignore' -Value "# Ignore logs`r`nlogs/`r`n"
  $updated = $true
} else {
  $ig = Get-Content '.gitignore' -Raw
  if ($ig -notmatch '(?m)^\s*logs/\s*$') {
    Add-Content -Path '.gitignore' -Value 'logs/'
    $updated = $true
  }
}

# Untrack logs from index (ignore errors if nothing tracked)
& git rm -r --cached --ignore-unmatch logs | Out-Null

# Commit ignore/untrack changes if any
if ($updated -or ((git status --porcelain) -ne '')) {
  git add -A
  git commit -m 'chore(git): ignore logs directory and untrack logs' -m $co | Out-Null
}

# Create a local backup ref before history rewrite
& git branch -f ("backup/{0}-pre-clean" -f $branch) $branch | Out-Null

# Rewrite branch history to remove logs/ from all commits
$env:FILTER_BRANCH_SQUELCH_WARNING = '1'
& git filter-branch --force --index-filter "git rm -r --cached --ignore-unmatch logs" --prune-empty -- $branch

# Cleanup refs created by filter-branch and aggressive GC
& git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
& git reflog expire --expire=now --all
& git gc --prune=now --aggressive

# Ensure remote exists
if (-not (git remote | Select-String -Quiet ("^" + [regex]::Escape($remoteName) + "$"))) {
  git remote add $remoteName $remoteUrl | Out-Null
}

# Force push rewritten branch
& git push -u $remoteName $branch --force

# Build and open PR URL
$head = 'main'
try {
  $hl = git remote show $remoteName | Select-String 'HEAD branch:'
  if ($hl) { $head = ($hl.ToString() -replace '.*:\s*','').Trim() }
} catch {}

$url = "https://github.com/nn-trading/ecosystem/compare/$head...$branch?expand=1"
Write-Host ("PR URL: {0}" -f $url) -ForegroundColor Green
Start-Process $url
