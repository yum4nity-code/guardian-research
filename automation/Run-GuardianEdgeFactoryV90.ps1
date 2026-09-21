param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v90_regime_gate_development.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V90 compile failed"}
Write-Host "=== GEF V90 - CONTROLLED REGIME GATE DEVELOPMENT 2010-2022 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V90 failed"}
