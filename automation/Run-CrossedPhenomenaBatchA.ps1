param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_crossed_batch_a_discovery.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }

Write-Host "=== GUARDIAN CROSSED ECONOMIC PHENOMENA - BATCH A ==="
Write-Host "P01 P04 P06 P08 P11 P12"
Write-Host "DISCOVERY: 2010-2012"
Write-Host "TEMPORAL HOLDOUT: 2013"
Write-Host "2014+: FORBIDDEN IN THIS RUN"
Write-Host "2026: FORBIDDEN"

py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Batch A Python compile failed" }

py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "Batch A discovery failed" }
