param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_crossed_batch_a_v2.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN CROSSED PHENOMENA - BATCH A V2 ==="
Write-Host "WARMUP: 2012"
Write-Host "DISCOVERY: 2013-2016"
Write-Host "HOLDOUT: 2017 - physically opened only after discovery freeze"
Write-Host "2018+: FORBIDDEN"
Write-Host "2026: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Batch A V2 compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "Batch A V2 failed" }
