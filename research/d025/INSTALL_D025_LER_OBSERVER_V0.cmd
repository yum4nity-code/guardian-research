@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_d025_ler_observer_v0.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo [Guardian] D025 LER Observer V0 deployment: OK
) else (
  echo [Guardian] D025 LER Observer V0 deployment: ERROR code=%RC%
)
pause
exit /b %RC%
