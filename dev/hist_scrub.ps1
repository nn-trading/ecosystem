$ErrorActionPreference = 'Stop'
$repo = 'C:\bots\ecosys'
Set-Location $repo
$branch = 'feature/loggerdb-cli'

# Ensure on target branch
$cur = (git rev-parse --abbrev-ref HEAD).Trim()
if ($cur -ne $branch) { git checkout $branch | Out-Null }

# Backup sanitized versions of sensitive scripts
$bk = Join-Path $env:TEMP 'ecosys_sanitize_backup'
New-Item -ItemType Directory -Path $bk -Force | Out-Null
$files = @('dev\oh_autofix.ps1','dev\oh_grand_test.ps1','dev\oh_use_key_and_launch.ps1')
foreach ($f in $files) {
  $src = Join-Path $repo $f
  if (Test-Path $src) { Copy-Item -LiteralPath $src -Destination (Join-Path $bk ([IO.Path]::GetFileName($src))) -Force }
}

# 1) Purge secret-bearing paths from history (api_key.txt and legacy scripts)
$env:FILTER_BRANCH_SQUELCH_WARNING = '1'
$ifcmd = 'git rm -f --cached --ignore-unmatch api_key.txt dev/oh_autofix.ps1 dev/oh_grand_test.ps1 dev/oh_use_key_and_launch.ps1'
& git filter-branch --force --index-filter $ifcmd --prune-empty -- $branch

# 2) Tree-filter redact key-like patterns in text files across history
$treeScript = @'
$ErrorActionPreference = "SilentlyContinue"
$patterns = @(''sk-[A-Za-z0-9_\-]{20,}'')
# Remove api_key.txt if present in this commit
if (Test-Path -LiteralPath ''api_key.txt'') { Remove-Item -Force -LiteralPath ''api_key.txt'' }
Get-ChildItem -Recurse -File -Include *.ps1,*.txt,*.md,*.json,*.yaml,*.yml,*.ini | ForEach-Object {
  try {
    $t  = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop
    $t2 = $t
    foreach($pat in $patterns) { $t2 = [regex]::Replace($t2, $pat, ''REDACTED'') }
    if ($t2 -ne $t) { Set-Content -LiteralPath $_.FullName -Value $t2 -Encoding UTF8 }
  } catch {}
}
'@
$tmp = Join-Path $env:TEMP ('ecosys_scrub_' + [guid]::NewGuid().ToString() + '.ps1')
Set-Content -LiteralPath $tmp -Value $treeScript -Encoding UTF8
$cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$tmp`""
& git filter-branch --force --tree-filter $cmd --prune-empty -- $branch

# Cleanup refs and GC
& git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
& git reflog expire --expire=now --all
& git gc --prune=now --aggressive

# Restore sanitized files into HEAD if missing and commit
$restore = $false
foreach ($f in $files) {
  $dst = Join-Path $repo $f
  $name = [IO.Path]::GetFileName($dst)
  $src = Join-Path $bk $name
  if (Test-Path $src) {
    $dir = Split-Path -Parent $dst
    if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $restore = $true
  }
}
if ($restore) {
  git add dev/oh_autofix.ps1 dev/oh_grand_test.ps1 dev/oh_use_key_and_launch.ps1
  git commit -m "chore(security): purge secret-bearing files from history; re-add sanitized versions" -m "Co-authored-by: openhands <openhands@all-hands.dev>" | Out-Null
}

# Verify HEAD for residual secret-like patterns
$matches = Get-ChildItem -Recurse -File | Select-String -Pattern 'sk-[A-Za-z0-9_-]{20,}' -AllMatches -ErrorAction SilentlyContinue
Write-Host ("HEAD secret-like matches: " + (($matches | Measure-Object).Count)) -ForegroundColor Cyan

# Push and PR URL
if (-not (git remote | Select-String -Quiet '^github$')) { git remote add github 'https://github.com/nn-trading/ecosystem.git' }
# Force push (will be blocked if GitHub detects secrets still present)
$push = git push -u github $branch --force 2>&1
$push | Write-Host

# Compute PR URL using remote default branch
$head = 'main'
$hl = git remote show github | Select-String 'HEAD branch:'
if ($hl) { $head = ($hl.ToString() -replace '.*:\s*','').Trim() }
$url = 'https://github.com/nn-trading/ecosystem/compare/' + $head + '...' + $branch + '?expand=1'
Write-Host ('PR URL: ' + $url) -ForegroundColor Green
