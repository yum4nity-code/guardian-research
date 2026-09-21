param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v84b_pre_v85_diagnostic.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V84B compile failed"}
Write-Host "=== GEF V84B - PRE-V85 ARCHITECTURE DIAGNOSTIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V84B failed"}
