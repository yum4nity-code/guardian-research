param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v97d_full_v93_panel_repair.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V97D compile failed"}
Write-Host "=== GEF V97D - FULL ORIGINAL V93 SCORED-PANEL TIMESTAMP REPAIR ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V97D failed"}
