@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Guardian-Monitor.ps1" -Root "D:\MT5_Backtests" -RefreshSeconds 15
