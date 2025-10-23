@echo off
setlocal enabledelayedexpansion
cd /d C:\bots\ecosys

echo [1/4] Killing any stuck probe processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'dev\\\\probe_events.py' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }"

echo [2/4] Rotating events.jsonl to last 50000 lines...
python dev\run_and_log.py "set KEEP_LAST=50000 && python dev\rotate_events.py"

echo [3/4] Probing events (tail=500)...
python dev\run_and_log.py "set PROBE_TAIL=500 && python dev\probe_events.py"

echo [4/4] Committing local changes (no push)...
git config --get user.name >nul 2>&1
IF ERRORLEVEL 1 git config user.name "openhands"

git config --get user.email >nul 2>&1
IF ERRORLEVEL 1 git config user.email "openhands@all-hands.dev"

git add -A
git commit -m "chore: rotate events to last 50k and validate headless run via probe" -m "Co-authored-by: openhands <openhands@all-hands.dev>" || echo No changes to commit.

echo Done.
