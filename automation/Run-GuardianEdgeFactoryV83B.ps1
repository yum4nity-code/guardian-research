param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v83b_rates_repair.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V83B compile failed"}
Write-Host "=== GEF V83B - RATES ASOF REPAIR ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V83B failed"}
