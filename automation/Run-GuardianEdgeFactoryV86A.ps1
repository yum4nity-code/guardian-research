param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v86a_top_raw_diagnostic.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V86A compile failed"}
Write-Host "=== GEF V86A - TOP RAW DIAGNOSTIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V86A failed"}
