@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\automation\Run-V111C1XAGUSDLockedOOSV2.ps1"
pause
