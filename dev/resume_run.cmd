@echo off
setlocal
set "REPO=C:\bots\ecosys"
set "PY=python"
set "KEEP_LAST=50000"
set "PROBE_TAIL=500"
set "STOP_AFTER=60"
set "HB=1"
set "HL=5"

echo [1/5] Kill stale probe/rotate processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'probe_events\.py|quick_probe\.py|rotate_events\.py|fast_rotate\.py' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }"

echo [2/5] Start headless for %STOP_AFTER%s...
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\dev\start_headless.ps1" -STOP_AFTER_SEC %STOP_AFTER% -HEARTBEAT_SEC %HB% -HEALTH_SEC %HL%

echo [3/5] Rotate events to last %KEEP_LAST% lines...
set KEEP_LAST=%KEEP_LAST% && "%PY%" "%REPO%\dev\fast_rotate.py"

echo [4/5] Probe last %PROBE_TAIL% events...
set PROBE_TAIL=%PROBE_TAIL% && "%PY%" "%REPO%\dev\quick_probe.py"

echo [5/5] Commit locally (no push)...
git -C "%REPO%" config --get user.name >NUL 2>&1 || git -C "%REPO%" config user.name "openhands"
git -C "%REPO%" config --get user.email >NUL 2>&1 || git -C "%REPO%" config user.email "openhands@all-hands.dev"
git -C "%REPO%" add -A
git -C "%REPO%" commit -m "chore: headless-run %STOP_AFTER%s, rotate %KEEP_LAST%, probe %PROBE_TAIL%" -m "Co-authored-by: openhands <openhands@all-hands.dev>" || echo No changes to commit.

echo Done.
endlocal
