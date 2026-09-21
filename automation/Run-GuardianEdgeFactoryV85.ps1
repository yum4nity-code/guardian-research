param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v85_selection_aware_discovery.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V85 compile failed"}
Write-Host "=== GEF V85 - CHECKPOINTED SELECTION-AWARE DISCOVERY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V85 failed"}
