@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_V111_C8_EURUSD_PRODUCTION_READINESS_v1_00.ps1"
pause
