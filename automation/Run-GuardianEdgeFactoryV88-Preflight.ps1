param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v88_replication_freeze_preflight.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V88 preflight compile failed"}
Write-Host "=== GEF V88 - FREEZE 2014-2017 REPLICATION PANEL + SOURCE PREFLIGHT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V88 preflight failed"}
