@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_D035_F1_FTMO_ONECLICK_v1_00.ps1"
pause
