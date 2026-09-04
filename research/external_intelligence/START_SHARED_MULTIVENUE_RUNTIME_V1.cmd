@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GUARDIAN SHARED MULTI-VENUE RUNTIME V1
echo ============================================================
echo BYBIT + BINANCE / READ ONLY / NO TRADING EFFECT
echo Singleton supervisor enabled: duplicate starts are ignored.
echo Ctrl+C to stop a manually launched supervisor.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] ERROR: local .venv missing. Run the multi-venue gate first.
  pause
  exit /b 2
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_shared_multivenue_autostart_v1.ps1"
set RC=%ERRORLEVEL%
echo.
echo [Guardian] Shared multi-venue supervisor stopped. code=%RC%
pause
exit /b %RC%
