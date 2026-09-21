param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v87_report_existing.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V87 report compile failed"}
Write-Host "=== GEF V87 - REPORT EXISTING COMPLETED RUN ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V87 report failed"}
