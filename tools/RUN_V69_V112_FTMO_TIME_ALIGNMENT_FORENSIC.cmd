@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_V69_V112_FTMO_TIME_ALIGNMENT_FORENSIC_v1_00.ps1"
pause
