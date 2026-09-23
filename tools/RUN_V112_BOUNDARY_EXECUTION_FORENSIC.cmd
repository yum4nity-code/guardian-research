@echo off
cd /d D:\MT5_Backtests\guardian-research
git pull
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0GUARDIAN_V112_BOUNDARY_EXECUTION_FORENSIC_v1_00.ps1"
pause
