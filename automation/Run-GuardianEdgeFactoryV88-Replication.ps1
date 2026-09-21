param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v88_replication_2014_2017.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V88 replication compile failed"}
Write-Host "=== GEF V88 - FROZEN 2014-2017 REPLICATION ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V88 replication failed"}
