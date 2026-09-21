param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v86_block_cluster_by_discovery.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V86 compile failed"}
Write-Host "=== GEF V86 - BLOCK-CLUSTER + GLOBAL BY DISCOVERY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V86 failed"}
