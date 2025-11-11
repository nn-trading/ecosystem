$ErrorActionPreference='SilentlyContinue'
Set-Location 'C:\bots\ecosys'

Write-Host 'Resetting any staged changes...' -ForegroundColor Cyan
git reset | Out-Host

Write-Host 'Aborting any rebase in progress if present...' -ForegroundColor Cyan
if (Test-Path .git\rebase-merge -or Test-Path .git\rebase-apply) { git rebase --abort | Out-Host }

Write-Host 'Current status:' -ForegroundColor Cyan
git status -sb | Out-Host

Write-Host 'Branches:' -ForegroundColor Cyan
git branch -a -vv | Out-Host

Write-Host 'HEAD ref:' -ForegroundColor Cyan
git rev-parse --abbrev-ref HEAD | Out-Host
