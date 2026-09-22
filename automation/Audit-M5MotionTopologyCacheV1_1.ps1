param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\audit_m5_motion_topology_cache_v1_1.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M5 topology V1.1 audit compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M5 topology V1.1 audit failed" }
