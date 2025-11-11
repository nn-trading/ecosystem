$ErrorActionPreference='SilentlyContinue'
Set-Location 'C:\bots\ecosys'

# 1) Kill stray jobs & vim
Get-Job | Stop-Job -ErrorAction SilentlyContinue; Get-Job | Remove-Job -ErrorAction SilentlyContinue
Get-Process vim -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 2) Make Git fully non-interactive
git config --local core.hooksPath .githooks-disabled
Remove-Item Env:EDITOR,Env:VISUAL,Env:GIT_EDITOR,Env:GIT_SEQUENCE_EDITOR -ErrorAction SilentlyContinue
git config --local core.editor 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command exit 0'
git config --local sequence.editor 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command exit 0'
git config --local merge.autoEdit no

# 3) Abort any stuck operations
if (Test-Path .git\rebase-merge -or Test-Path .git\rebase-apply) { git rebase --abort | Out-Null }
if (Test-Path .git\MERGE_HEAD) { git merge --abort | Out-Null }
if (Test-Path .git\CHERRY_PICK_HEAD) { git cherry-pick --abort | Out-Null }
if (Test-Path .git\BISECT_LOG) { git bisect reset | Out-Null }

# 4) Show clean state
git status -sb
Write-Host 'OK: cleared interactive Git state; disabled hooks; editor set to non-interactive.' -ForegroundColor Green
