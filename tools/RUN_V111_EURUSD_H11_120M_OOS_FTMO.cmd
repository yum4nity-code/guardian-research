@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_V111_EURUSD_H11_120M_OOS_FTMO_v1_00.ps1"
pause
