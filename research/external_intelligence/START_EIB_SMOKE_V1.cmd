@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "VENV=%~dp0.venv"
set "PY=%VENV%\Scripts\python.exe"

if not exist "%PY%" (
  echo [EIB] Creation de l'environnement Python local...
  py -3 -m venv "%VENV%" 2>nul
  if errorlevel 1 (
    python -m venv "%VENV%"
    if errorlevel 1 goto :pyfail
  )
)

echo [EIB] Installation/verif des dependances...
"%PY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :pipfail

echo.
echo [EIB] Smoke live 35 minutes BTC + ETH.
echo [EIB] Donnees: D:\MT5_Backtests\Research\ExternalIntelligence
echo [EIB] Laisse cette fenetre ouverte jusqu'au resume final.
echo.
"%PY%" smoke_v1.py --minutes 35 --data-dir "D:\MT5_Backtests\Research\ExternalIntelligence"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [EIB] Smoke termine: PASS.
) else (
  echo [EIB] Smoke termine avec code %RC%. Le resume indiquera quoi verifier.
)
echo.
pause
exit /b %RC%

:pyfail
echo [EIB][ERREUR] Python 3 introuvable. Installe Python 3 ou rends 'py'/'python' accessible dans PATH.
pause
exit /b 10

:pipfail
echo [EIB][ERREUR] Impossible d'installer aiohttp depuis requirements.txt.
pause
exit /b 11
