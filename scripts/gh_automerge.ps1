param(
  [string]$Owner = "nn-trading",
  [string]$Repo = "ecosystem",
  [string]$Base = "main",
  [string]$Branch = "feature/autonomy-core",
  [switch]$DeleteBranchAfterMerge
)

$ErrorActionPreference = "Stop"
function Step($m){ Write-Host ("==> " + $m) }

# Try to populate GITHUB_TOKEN from secrets file if not set
if (-not $env:GITHUB_TOKEN) {
  $tkPath = "C:\bots\ecosys\secrets\github_token.txt"
  if (Test-Path $tkPath) {
    $env:GITHUB_TOKEN = (Get-Content $tkPath -Raw).Trim()
  }
}

# Ensure 'github' remote points to the right repo
$remoteUrl = "https://github.com/$Owner/$Repo.git"
if (-not (git remote | Select-String "^github$")) {
  Step "Adding github remote"
  git remote add github $remoteUrl | Out-Null
} else {
  Step "Ensuring github remote URL"
  git remote set-url github $remoteUrl | Out-Null
}

Step "Fetch remotes"
git fetch github | Out-Null

# Make sure the feature branch exists locally and is pushed
Step "Ensure branch pushed"
if (-not (git branch --list $Branch)) {
  if (git branch -r | Select-String "github/$Branch") {
    git switch -c $Branch --track github/$Branch | Out-Null
  }
}
# Only push if local is ahead of remote
$needsPush = $false
try {
  $counts = git rev-list --left-right --count "github/$Branch...$Branch" 2>$null
  if ($counts) {
    $parts = $counts.Trim() -split "\s+"
    if ($parts.Length -ge 2) { $needsPush = [int]$parts[1] -gt 0 }
  }
} catch {}
if ($needsPush) {
  git push -u github $Branch 2>$null | Out-Null
} else {
  Step "Remote branch already up-to-date"
}

$compareUrl = "https://github.com/$Owner/$Repo/compare/$Base...${Branch}?expand=1"

# If no token, open compare page for manual PR
if (-not $env:GITHUB_TOKEN -or [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
  Write-Host "GITHUB_TOKEN not set. Opening compare URL for manual PR:"
  Write-Host $compareUrl
  Start-Process $compareUrl | Out-Null
  exit 0
}

$headers = @{
  "Authorization" = "Bearer $($env:GITHUB_TOKEN)"
  "Accept"        = "application/vnd.github+json"
  "X-GitHub-Api-Version" = "2022-11-28"
  "User-Agent"    = "ecosys-automerge"
}

# Find open PR for head/base
Step "Find existing PR"
$prs = Invoke-RestMethod -Method Get -Headers $headers -Uri ("https://api.github.com/repos/{0}/{1}/pulls?state=open&head={0}:{2}&base={3}" -f $Owner,$Repo,$Branch,$Base)
$pr = $null
if ($prs -and $prs.Count -gt 0) { $pr = $prs[0] }

if (-not $pr) {
  Step "Create PR"
  $body = @{
    title = "feat(autonomy): Autonomy core + one-click launcher + smoke"
    head  = $Branch
    base  = $Base
    body  = @"
- One-click Start-Ecosystem.bat (root + Desktop)
- Foreground smoke via start.ps1 prints:
  start.ps1 path, DB path, screenshot path, provider
- Bus + events + orchestrator (Comm/Brain/Worker/Tester/Logger)
- Memory logger to var/events.db
- LLM providers: OpenAI (live OK), OpenRouter (401 pending key/header), GPT-OSS stub
- README/STATUS updated; tests green; probes saved in reports/llm
"@
    draft = $false
  } | ConvertTo-Json -Depth 5
  $pr = Invoke-RestMethod -Method Post -Headers $headers -Uri "https://api.github.com/repos/$Owner/$Repo/pulls" -Body $body
}

Write-Host ("PR: " + $pr.html_url)

# Try to merge (will fail gracefully if protections/review required)
Step "Attempt merge"
$mergeBody = @{ merge_method = "squash" } | ConvertTo-Json
$merged = $false
try {
  $mergeRes = Invoke-RestMethod -Method Put -Headers $headers -Uri ("https://api.github.com/repos/{0}/{1}/pulls/{2}/merge" -f $Owner,$Repo,$pr.number) -Body $mergeBody
  $merged = ($mergeRes.merged -eq $true)
} catch {
  $merged = $false
}

if (-not $merged) {
  Write-Host "Could not auto-merge (likely branch protections or reviews). Opening PR and exiting."
  Start-Process $pr.html_url | Out-Null
  exit 0
}

Write-Host ("Merged PR #" + $pr.number)

# Sync local main
Step "Sync local main"
git fetch github | Out-Null
git switch $Base | Out-Null
git reset --hard "github/$Base" | Out-Null

# Optionally delete feature branch locally & on GitHub
if ($DeleteBranchAfterMerge) {
  Step "Deleting feature branch locally and remotely"
  git branch -D $Branch 2>$null | Out-Null
  git push github (":{0}" -f $Branch) 2>$null | Out-Null
}

# Run maintenance smoke if available
if (Test-Path ".\scripts\maint_sweep.ps1") {
  Step "Run maintenance sweep"
  powershell -NoProfile -File .\scripts\maint_sweep.ps1
}

Write-Host "DONE: main is synced."
Write-Host "Launcher: Start-Ecosystem.bat"
Write-Host ("Compare: " + $compareUrl)
