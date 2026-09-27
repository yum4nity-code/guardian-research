param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\diagnose_m09_m10_validity_support.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN M09/M10 VALIDITY SUPPORT AUDIT ===" -ForegroundColor Cyan
Write-Host "READ-ONLY ANALYSIS OF EXISTING DISCOVERY RUN"
Write-Host "NO NEW MARKET DATA | NO NEW OOS | 2026 UNTOUCHED"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "diagnostic compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "diagnostic failed" }
