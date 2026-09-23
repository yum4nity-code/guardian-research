@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_V69_V112_EXECUTION_AUDIT_v1_01.ps1"
pause
