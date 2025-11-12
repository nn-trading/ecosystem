@echo off
set "REPO=C:\bots\ecosys"
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\start.ps1" -Headless 1 -Background 0
pause

