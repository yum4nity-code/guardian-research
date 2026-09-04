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

echo [Guardian] Shared Intelligence V1 demarre.
echo [Guardian] Une seule collecte + un seul moteur pour toutes les instances Guardian.
echo [Guardian] Snapshot: D:\MT5_Backtests\Research\ExternalIntelligence\market_state_v1.json
echo [Guardian] Ctrl+C pour arreter.
".venv\Scripts\python.exe" shared_service_v1.py --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
set RC=%ERRORLEVEL%
echo.
echo [Guardian] Service arrete. Code %RC%.
pause
exit /b %RC%
