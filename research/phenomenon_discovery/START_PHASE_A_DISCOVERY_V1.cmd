@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_PHASE_A_DISCOVERY_V1.ps1" %*
exit /b %ERRORLEVEL%
