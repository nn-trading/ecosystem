$ErrorActionPreference = 'Stop'
$repoRoot = 'C:\bots\ecosys'
$branch   = 'feature/loggerdb-cli'
$co       = 'Co-authored-by: openhands <openhands@all-hands.dev>'
Set-Location -LiteralPath $repoRoot

# Ensure on target branch
$cur = (git rev-parse --abbrev-ref HEAD).Trim()
if ($cur -ne $branch) { git checkout $branch }

# Ensure .gitignore has logs/ and api_key.txt
$igPath = '.gitignore'
if (!(Test-Path -LiteralPath $igPath)) { Set-Content -Encoding UTF8 -LiteralPath $igPath -Value "logs/`r`napi_key.txt`r`n" }
else {
  $ig = Get-Content -LiteralPath $igPath -Raw
  $changed = $false
  if ($ig -notmatch '(?m)^\s*logs/\s*$') { Add-Content -LiteralPath $igPath -Value 'logs/'; $changed = $true }
  if ($ig -notmatch '(?m)^\s*api_key.txt\s*$') { Add-Content -LiteralPath $igPath -Value 'api_key.txt'; $changed = $true }
}

# Remove api_key.txt and redact keys in known scripts
if (Test-Path -LiteralPath 'api_key.txt') { Remove-Item -Force -LiteralPath 'api_key.txt' }
$files = @('dev\oh_autofix.ps1','dev\oh_grand_test.ps1','dev\oh_use_key_and_launch.ps1')
foreach ($f in $files) {
  if (Test-Path -LiteralPath $f) {
    $t  = Get-Content -LiteralPath $f -Raw
    $t2 = [regex]::Replace($t, 'sk-[A-Za-z0-9_\-]{20,}', 'REDACTED')
    if ($t2 -ne $t) { Set-Content -Encoding Ascii -LiteralPath $f -Value $t2 }
  }
}

if ((git status --porcelain) -ne '') { git add -A; git commit -m 'chore(security): redact secrets and ignore api_key.txt' -m $co }

# Ensure tree-filter scrubber exists
$tf = 'dev\_treefilter_scrub.ps1'
if (!(Test-Path -LiteralPath $tf)) {
  Set-Content -Encoding Ascii -LiteralPath $tf -Value @'
$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath "api_key.txt") { Remove-Item -Force -LiteralPath "api_key.txt" }
$files = @("dev\oh_autofix.ps1","dev\oh_grand_test.ps1","dev\oh_use_key_and_launch.ps1")
foreach ($f in $files) {
  if (Test-Path -LiteralPath $f) {
    try {
      $txt  = Get-Content -LiteralPath $f -Raw
      $txt2 = [regex]::Replace($txt, 'sk-[A-Za-z0-9_\-]{20,}', 'REDACTED')
      if ($txt2 -ne $txt) { Set-Content -Encoding Ascii -LiteralPath $f -Value $txt2 }
    } catch {}
  }
}
'@
}

# Rewrite history to scrub secrets across the branch
$env:FILTER_BRANCH_SQUELCH_WARNING = '1'
& git filter-branch --force --tree-filter "powershell -NoProfile -ExecutionPolicy Bypass -File dev/_treefilter_scrub.ps1" --prune-empty -- $branch

# Clean original refs and GC
& git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
& git reflog expire --expire=now --all
& git gc --prune=now --aggressive

# Verify no openai-like keys remain in working tree
$allFiles = Get-ChildItem -Recurse -File | Select-Object -ExpandProperty FullName
$matches = @()
foreach ($p in $allFiles) { try { $matches += Select-String -Path $p -Pattern 'sk-[A-Za-z0-9_\-]{20,}' -ErrorAction SilentlyContinue } catch {} }
Write-Host ("Remaining secrets matches: {0}" -f (($matches | Measure-Object).Count)) -ForegroundColor Cyan

# Push force to GitHub
if (-not (git remote | Select-String -Quiet '^github$')) { git remote add github 'https://github.com/nn-trading/ecosystem.git' }
& git push -u github $branch --force

# Build PR URL
$head = 'main'
$hl = git remote show github | Select-String 'HEAD branch:'
if ($hl) { $head = ($hl.ToString() -replace '.*:\s*','').Trim() }
$url = "https://github.com/nn-trading/ecosystem/compare/$head...$branch?expand=1"
Write-Host ("PR URL: {0}" -f $url) -ForegroundColor Green
