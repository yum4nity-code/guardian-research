param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v85b_block_null_benchmark.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V85B compile failed"}
Write-Host "=== GEF V85B - 28-DAY BLOCK NULL BENCHMARK ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V85B failed"}
