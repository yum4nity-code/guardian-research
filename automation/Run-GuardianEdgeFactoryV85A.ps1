param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v85a_bh_explosion_diagnostic.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V85A compile failed"}
Write-Host "=== GEF V85A - BH EXPLOSION DIAGNOSTIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V85A failed"}
