param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v95_execution_data_artifact_audit.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V95 compile failed"}
Write-Host "=== GEF V95 - EXECUTION + DATA-ARTIFACT AUDIT / FROZEN 3 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V95 failed"}
