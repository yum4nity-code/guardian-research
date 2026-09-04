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
echo === 1/2 TESTS OFFLINE MT5 COMMON BRIDGE V1 ===
".venv\Scripts\python.exe" -m unittest discover -s tests -p "test_mt5_common_bridge_v1.py" -v
if errorlevel 1 (
  echo.
  echo [Guardian] ECHEC tests offline. Smoke annule.
  pause
  exit /b 4
)

echo.
echo === 2/2 SMOKE LIVE MT5 FILE_COMMON BRIDGE - 2 MINUTES ===
".venv\Scripts\python.exe" smoke_mt5_common_bridge_v1.py --minutes 2 --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
set RC=%ERRORLEVEL%

if "%RC%"=="0" (
  echo.
  echo [Guardian] FULL GATE MT5 COMMON BRIDGE V1: PASS.
) else (
  echo.
  echo [Guardian] FULL GATE MT5 COMMON BRIDGE V1: REVIEW / code %RC%.
)
pause
exit /b %RC%
