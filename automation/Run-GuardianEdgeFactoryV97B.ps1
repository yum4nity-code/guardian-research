param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v97b_source_time_semantics.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V97B compile failed"}
Write-Host "=== GEF V97B - SOURCE TIME SEMANTICS FORENSIC / FREEZE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V97B failed"}
