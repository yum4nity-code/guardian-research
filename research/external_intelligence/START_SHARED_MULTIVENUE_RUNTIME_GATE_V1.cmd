@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GUARDIAN SHARED MULTI-VENUE RUNTIME V1 GATE
echo ============================================================
echo One Bybit collector + one Binance collector + one state engine
echo + one MT5 FILE_COMMON bridge. READ ONLY / NO TRADING EFFECT.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] ERROR: local .venv missing. Run the Binance multi-venue gate first.
  pause
  exit /b 2
)

".venv\Scripts\python.exe" shared_runtime_multivenue_bridge_v1.py --run-seconds 75 --gate --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
if errorlevel 1 goto :fail

echo.
echo [Guardian] FULL GATE SHARED MULTI-VENUE RUNTIME V1: PASS.
pause
exit /b 0

:fail
echo.
echo [Guardian] SHARED MULTI-VENUE RUNTIME V1 GATE: REVIEW.
pause
exit /b 1
