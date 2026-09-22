param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v97a_timebase_forensic.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V97A compile failed"}
Write-Host "=== GEF V97A - HISTDATA / FTMO TIMEBASE FORENSIC ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V97A failed"}
