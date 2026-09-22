param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v96_parent_interaction_attribution.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V96 compile failed"}
Write-Host "=== GEF V96 - PARENT / INTERACTION ATTRIBUTION OF FROZEN 3 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V96 failed"}
