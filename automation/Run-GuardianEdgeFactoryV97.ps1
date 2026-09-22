param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v97_ftmo_historical_bridge.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V97 compile failed"}
Write-Host "=== GEF V97 - FTMO HISTORICAL FEED / SIGNAL BRIDGE 2023-2025 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V97 failed"}
