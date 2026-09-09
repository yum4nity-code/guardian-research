@echo off
setlocal
title Guardian Research - Live Status
:loop
cls
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK_GUARDIAN.ps1"
echo.
echo Rafraichissement toutes les 5 secondes - Ctrl+C pour fermer.
timeout /t 5 /nobreak >nul
goto loop
