@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GUARDIAN MT5 MULTI-VENUE BRIDGE V1 GATE
echo ============================================================
echo Uses the already validated market_state_multivenue_v1.json.
echo No network collection. No trading effect.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] ERROR: local .venv missing. Run the Binance multi-venue gate first.
  pause
  exit /b 2
)

echo === 1/2 OFFLINE BRIDGE TESTS ===
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_mt5_common_bridge_multivenue_v1.py" -v
if errorlevel 1 goto :fail

echo.
echo === 2/2 PUBLISH VALIDATED SNAPSHOT INTO MT5 FILE_COMMON ===
".venv\Scripts\python.exe" gate_mt5_multivenue_bridge_v1.py --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
if errorlevel 1 goto :fail

echo.
echo [Guardian] FULL GATE MT5 MULTI-VENUE BRIDGE V1: PASS.
pause
exit /b 0

:fail
echo.
echo [Guardian] MT5 MULTI-VENUE BRIDGE V1 GATE: REVIEW.
pause
exit /b 1
