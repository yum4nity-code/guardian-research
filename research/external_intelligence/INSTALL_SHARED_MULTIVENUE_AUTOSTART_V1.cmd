@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GUARDIAN SHARED INTELLIGENCE - INSTALL AUTOSTART V1
echo BYBIT + BINANCE / READ ONLY
echo ============================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_shared_multivenue_autostart_v1.ps1"
set RC=%ERRORLEVEL%
echo.
if %RC% EQU 0 (
  echo [Guardian] AUTOSTART INSTALL: OK
) else (
  echo [Guardian] AUTOSTART INSTALL: ERROR code=%RC%
)
echo.
pause
exit /b %RC%
