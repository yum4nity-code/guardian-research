@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
py -3 "%~dp0collect_v69_v112_engine_source_scan_v1_00.py"
if errorlevel 1 (
  echo.
  echo === SOURCE SCAN FAILED ===
) else (
  echo.
  echo === SOURCE SCAN COMPLETE ===
  echo Envoie le ZIP GUARDIAN_V69_V112_ENGINE_SOURCE_SCAN_... du Bureau dans ChatGPT.
)
pause
