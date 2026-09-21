param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v91_locked_oos_2023_2025.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V91 compile failed"}
Write-Host "=== GEF V91 - LOCKED OOS 2023-2025 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V91 failed"}
