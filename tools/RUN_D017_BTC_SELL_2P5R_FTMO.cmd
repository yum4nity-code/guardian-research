@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_D017_BTC_SELL_2P5R_FTMO_v1_00.ps1"
pause
