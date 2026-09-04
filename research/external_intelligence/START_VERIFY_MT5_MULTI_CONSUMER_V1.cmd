@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] ERREUR: .venv absent. Lancez d'abord un gate/runtime EIB.
  pause
  exit /b 2
)
".venv\Scripts\python.exe" verify_mt5_multi_consumer_v1.py
set RC=%ERRORLEVEL%
pause
exit /b %RC%
