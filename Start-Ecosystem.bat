@echo off&setlocal&cd /d "%~dp0"&powershell -NoProfile -ExecutionPolicy Bypass -File "./start.ps1" -Headless 1 -Background 0&echo.&pause
