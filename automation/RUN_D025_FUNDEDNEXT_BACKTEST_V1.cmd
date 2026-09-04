@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_d025_fundednext_backtest_v1.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" echo [Guardian] D025 FundedNext backtest ended with error code %RC%.
pause
exit /b %RC%
