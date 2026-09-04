@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GUARDIAN SHARED MULTI-VENUE RUNTIME V1
echo ============================================================
echo BYBIT + BINANCE / READ ONLY / NO TRADING EFFECT
echo Leave this window open while Guardian consumes Shared Intel.
echo Ctrl+C to stop.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] ERROR: local .venv missing. Run the multi-venue gate first.
  pause
  exit /b 2
)

".venv\Scripts\python.exe" shared_runtime_multivenue_bridge_v1.py --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
set RC=%ERRORLEVEL%
echo.
echo [Guardian] Shared multi-venue runtime stopped. code=%RC%
pause
exit /b %RC%
