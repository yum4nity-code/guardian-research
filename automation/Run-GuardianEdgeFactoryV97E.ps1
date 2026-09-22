param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v97e_corrected_2026_freeze.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V97E compile failed"}
Write-Host "=== GEF V97E - CORRECTED 2026 FORWARD FREEZE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V97E failed"}
