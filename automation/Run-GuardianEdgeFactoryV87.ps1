param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v87_frozen_panel_2013_confirmation.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V87 compile failed"}
Write-Host "=== GEF V87 - FROZEN 100-CANDIDATE PANEL + 2013 CONFIRMATION ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V87 failed"}
