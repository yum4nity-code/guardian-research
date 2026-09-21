param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v82d_cftc_recovery.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V82D compile failed"}
Write-Host "=== GEF V82D - VALIDATED CFTC CAUSAL RECOVERY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V82D failed"}
