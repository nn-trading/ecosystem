@echo off
setlocal
set "REPO=C:\bots\ecosys"
set "KEEP_LAST=50000"
set "PROBE_TAIL=500"
set "STOP_AFTER=60"
set "HB=1"
set "HL=5"
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\dev\resume_run.ps1" -STOP_AFTER_SEC %STOP_AFTER% -HEARTBEAT_SEC %HB% -HEALTH_SEC %HL% -KEEP_LAST %KEEP_LAST% -PROBE_TAIL %PROBE_TAIL%
endlocal
