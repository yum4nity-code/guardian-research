param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v88a_incremental_attribution_panel48.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V88A compile failed"}
Write-Host "=== GEF V88A - PANEL 48 INCREMENTAL ATTRIBUTION ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V88A failed"}
