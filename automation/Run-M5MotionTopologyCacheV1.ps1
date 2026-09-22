param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_m5_motion_topology_build_v1.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN M5 MOTION TOPOLOGY FACTORY V1 - CACHE BUILD ==="
Write-Host "SOURCE: 2011-2014 ONLY"
Write-Host "DISCOVERY OUTCOMES: 2012-2014"
Write-Host "2015+: FORBIDDEN"
Write-Host "EDGE TESTS: ZERO"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M5 topology builder compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M5 topology cache build failed" }
