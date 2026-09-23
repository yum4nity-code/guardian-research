@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_V69_V112_EXACT_SOURCE_FTMO_AUDIT_v1_00.ps1"
pause
