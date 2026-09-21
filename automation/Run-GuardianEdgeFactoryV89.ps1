param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v89_primary_validation_2018_2022.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V89 compile failed"}
Write-Host "=== GEF V89 - FROZEN PRIMARY EDGE VALIDATION 2018-2022 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V89 failed"}
