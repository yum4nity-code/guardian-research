param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v99_execution_reality_audit.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V99 compile failed"}
Write-Host "=== GEF V99 - EXACT M1 EXECUTION REALITY AUDIT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V99 failed"}
