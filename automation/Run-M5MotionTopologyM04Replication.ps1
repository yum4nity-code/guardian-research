param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_m5_motion_topology_m04_replication.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN M5 M04 2015-2017 REPLICATION ==="
Write-Host "FROZEN VARIANTS: 6"
Write-Host "RAW HISTORY: 2011-2017"
Write-Host "REPLICATION: 2015-2017"
Write-Host "2018+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M04 replication compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M04 replication failed" }
