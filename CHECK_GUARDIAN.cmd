@echo off
setlocal
title Guardian Research - Status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK_GUARDIAN.ps1"
echo.
echo Si c'est ROUGE, copie-moi simplement ce qui est affiche ici.
echo.
pause
