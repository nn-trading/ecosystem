@echo off
set "REPO=C:\bots\ecosys"
start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%\start.ps1" -Headless 1 -Background 1

