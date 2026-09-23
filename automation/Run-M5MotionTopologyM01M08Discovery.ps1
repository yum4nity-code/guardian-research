param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_m5_motion_topology_m01_m08_discovery.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN M5 MOTION TOPOLOGY M01-M08 DISCOVERY ==="
Write-Host "DISCOVERY OUTCOMES: 2012-2014 ONLY"
Write-Host "PREDECLARED VARIANTS: 291"
Write-Host "2015+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M01-M08 discovery compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M01-M08 discovery failed" }
