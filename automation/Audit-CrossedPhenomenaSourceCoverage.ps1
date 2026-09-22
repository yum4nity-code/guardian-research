param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\audit_crossed_phenomena_source_coverage.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Coverage audit compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "Coverage audit failed" }
