@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GUARDIAN SHARED INTELLIGENCE - REMOVE AUTOSTART V1
echo ============================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_shared_multivenue_autostart_v1.ps1" -Remove
set RC=%ERRORLEVEL%
echo.
if %RC% EQU 0 (
  echo [Guardian] AUTOSTART REMOVE: OK
) else (
  echo [Guardian] AUTOSTART REMOVE: ERROR code=%RC%
)
echo.
pause
exit /b %RC%
