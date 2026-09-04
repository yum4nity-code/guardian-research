@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GUARDIAN BINANCE MULTI-VENUE V1 GATE
echo ============================================================
echo IMPORTANT: stop START_SHARED_RUNTIME_COVERAGE_BRIDGE_V1 first
echo so this gate is the only Bybit writer during the live smoke.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] Creating local Python environment...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] ERROR: Python/venv unavailable.
  pause
  exit /b 2
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt >nul
if errorlevel 1 (
  echo [Guardian] ERROR installing dependencies.
  pause
  exit /b 3
)

echo === 1/2 OFFLINE TESTS ===
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_binance_collector_v1.py" -v
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_market_state_multivenue_v1.py" -v
if errorlevel 1 goto :fail

echo.
echo === 2/2 LIVE BYBIT + BINANCE MULTI-VENUE SMOKE - 3 MINUTES ===
".venv\Scripts\python.exe" smoke_binance_multivenue_v1.py --minutes 3 --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
if errorlevel 1 goto :fail

echo.
echo [Guardian] FULL GATE BINANCE MULTI-VENUE V1: PASS.
pause
exit /b 0

:fail
echo.
echo [Guardian] BINANCE MULTI-VENUE V1 GATE: REVIEW.
pause
exit /b 1
