@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_EA01_XAU_FTMO_TRANSPORT_v1_00.ps1"
pause
