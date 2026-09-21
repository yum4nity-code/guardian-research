param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v83_multiresolution_build.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V83 compile failed"}
Write-Host "=== GEF V83 - CORRECTED MULTIRESOLUTION CAUSAL BUILD ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V83 failed"}
