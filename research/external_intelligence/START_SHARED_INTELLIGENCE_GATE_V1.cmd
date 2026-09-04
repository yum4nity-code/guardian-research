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
echo === 1/2 TESTS OFFLINE MARKET_STATE_V1 ===
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_market_state_v1.py" -v
if errorlevel 1 (
  echo.
  echo [Guardian] ECHEC tests offline. Smoke annule.
  pause
  exit /b 4
)

echo.
echo === 2/2 SMOKE LIVE SHARED INTELLIGENCE V1 - 3 MINUTES ===
".venv\Scripts\python.exe" smoke_shared_service_v1.py --minutes 3 --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
set RC=%ERRORLEVEL%

if "%RC%"=="0" (
  echo.
  echo [Guardian] FULL GATE SHARED INTELLIGENCE V1: PASS.
) else (
  echo.
  echo [Guardian] FULL GATE SHARED INTELLIGENCE V1: REVIEW / code %RC%.
)
pause
exit /b %RC%
