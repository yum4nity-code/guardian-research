param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v92_clean_temporal_ladder.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V92 compile failed"}
Write-Host "=== GEF V92 - CLEAN BROAD TEMPORAL LADDER (2023+ LOCKED) ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V92 failed"}
