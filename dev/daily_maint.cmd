@echo off
setlocal
set "REPO=C:\bots\ecosys"
set "PY=python"
set "KEEP_LAST=50000"
set "PROBE_TAIL=500"
echo [Daily] Rotate to %KEEP_LAST% lines...
set KEEP_LAST=%KEEP_LAST% && "%PY%" "%REPO%\dev\fast_rotate.py"
echo [Daily] Probe last %PROBE_TAIL% lines...
set PROBE_TAIL=%PROBE_TAIL% && "%PY%" "%REPO%\dev\quick_probe.py"
endlocal
