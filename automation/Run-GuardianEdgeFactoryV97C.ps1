param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v97c_corrected_time_rescore.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V97C compile failed"}
Write-Host "=== GEF V97C - CORRECTED TIME RESCORE OF FROZEN 3 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V97C failed"}
