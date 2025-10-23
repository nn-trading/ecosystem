@echo off
setlocal
set "REPO=C:\bots\ecosys"
set "PY=python"
set "KEEP_LAST=50000"
set "PROBE_TAIL=500"
set "STOP_AFTER=300"
set "HB=1"
set "HL=5"
set "LOG=%REPO%\logs\loop.log"
if not exist "%REPO%\logs" mkdir "%REPO%\logs"
if not exist "%REPO%\logs\probes" mkdir "%REPO%\logs\probes"

:loop
for /f "delims=" %%A in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%A
echo === %date% %time% START CYCLE ===>> "%LOG%"

echo [Loop] Start headless for %STOP_AFTER%s...>> "%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\dev\start_headless.ps1" -STOP_AFTER_SEC %STOP_AFTER% -HEARTBEAT_SEC %HB% -HEALTH_SEC %HL% >> "%LOG%" 2>>&1

echo [Loop] Rotate events to last %KEEP_LAST% lines...>> "%LOG%"
set KEEP_LAST=%KEEP_LAST% && "%PY%" "%REPO%\dev\fast_rotate.py" >> "%LOG%" 2>>&1

echo [Loop] Probe last %PROBE_TAIL% events...>> "%LOG%"
powershell -NoProfile -Command "$env:PROBE_TAIL='%PROBE_TAIL%'; $o = & python '%REPO%\dev\quick_probe.py'; $o; $o | Out-File -Encoding UTF8 '%REPO%\logs\probes\probe_%TS%.json'" >> "%LOG%" 2>>&1

echo [Loop] Sleep 10s before next cycle...>> "%LOG%"
timeout /t 10 /nobreak >> "%LOG%" 2>>&1
goto loop
