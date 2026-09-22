param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\diagnose_crossed_batch_a_v2_object_support.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Object support diagnostic compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "Object support diagnostic failed" }
