@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] Creation de l'environnement Python local...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
  echo [Guardian] ERREUR: Python/venv indisponible.
  pause
  exit /b 2
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt >nul
if errorlevel 1 (
  echo [Guardian] ERREUR installation dependances.
  pause
  exit /b 3
)

echo [Guardian] Smoke Shared Intelligence V1 - 3 minutes BTC + ETH.
echo [Guardian] Donnees: D:\MT5_Backtests\Research\ExternalIntelligence
".venv\Scripts\python.exe" smoke_shared_service_v1.py --minutes 3 --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
set RC=%ERRORLEVEL%

if "%RC%"=="0" (
  echo.
  echo [Guardian] Shared Intelligence smoke: PASS.
) else (
  echo.
  echo [Guardian] Shared Intelligence smoke: REVIEW / code %RC%.
)
pause
exit /b %RC%
