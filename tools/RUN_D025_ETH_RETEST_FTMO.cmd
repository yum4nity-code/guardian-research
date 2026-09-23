@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_D025_ETH_RETEST_FTMO_v1_00.ps1"
pause
