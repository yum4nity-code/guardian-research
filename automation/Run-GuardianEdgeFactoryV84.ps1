param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v84_corrected_engine_benchmark.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V84 compile failed"}
Write-Host "=== GEF V84 - CORRECTED 5M ENGINE BENCHMARK ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V84 failed"}
