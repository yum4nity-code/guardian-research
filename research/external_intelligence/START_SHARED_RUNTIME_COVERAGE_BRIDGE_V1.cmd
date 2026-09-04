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

echo.
echo [Guardian] Demarrage du runtime partage couverture + bridge.
echo [Guardian] Gardez cette fenetre ouverte pendant le test MT5.
echo [Guardian] Arret: Ctrl+C.
echo.
".venv\Scripts\python.exe" shared_runtime_coverage_bridge_v1.py --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
