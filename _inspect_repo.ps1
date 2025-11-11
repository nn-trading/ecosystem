$ErrorActionPreference='SilentlyContinue'
Set-Location 'C:\bots\ecosys'

Write-Host 'Top-level items:' -ForegroundColor Cyan
Get-ChildItem -Force | Select-Object Mode,Name,Length | Sort-Object Name

Write-Host '---' -ForegroundColor DarkGray
Write-Host 'Git status:' -ForegroundColor Cyan
git status -sb

Write-Host '---' -ForegroundColor DarkGray
Write-Host 'Branches:' -ForegroundColor Cyan
git branch -a -vv

Write-Host '---' -ForegroundColor DarkGray
Write-Host 'Remotes:' -ForegroundColor Cyan
git remote -v

Write-Host '---' -ForegroundColor DarkGray
Write-Host 'Current branch:' -ForegroundColor Cyan
git rev-parse --abbrev-ref HEAD

Write-Host '---' -ForegroundColor DarkGray
Write-Host 'Recent commits:' -ForegroundColor Cyan
git log --oneline --decorate --graph -n 10

Write-Host '---' -ForegroundColor DarkGray
if (Test-Path .gitignore) {
  Write-Host '.gitignore:' -ForegroundColor Cyan
  Get-Content .gitignore -TotalCount 200
} else {
  Write-Host '.gitignore: (missing)' -ForegroundColor Yellow
}

Write-Host '---' -ForegroundColor DarkGray
Write-Host 'Git user config:' -ForegroundColor Cyan
git config user.name
git config user.email
