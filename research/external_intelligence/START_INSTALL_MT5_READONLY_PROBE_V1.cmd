@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_mt5_probe_v1.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
