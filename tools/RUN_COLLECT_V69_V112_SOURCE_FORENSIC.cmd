@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
py -3 "%~dp0collect_v69_v112_source_forensic_v1_00.py"
if errorlevel 1 (
  echo.
  echo === COLLECTOR FAILED ===
) else (
  echo.
  echo === COLLECTOR COMPLETE ===
  echo Envoie le ZIP GUARDIAN_V69_V112_SOURCE_FORENSIC_... depuis ton Bureau dans ChatGPT.
)
pause
