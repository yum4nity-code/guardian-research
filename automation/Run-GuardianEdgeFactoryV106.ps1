param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_v106_remaining_source_audit.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GEF V106 - REMAINING CAUSAL SOURCE AUDIT ==="
Write-Host "EDGE TRIALS: ZERO"
Write-Host "2023-2025 MARKET RETURNS: FORBIDDEN"
Write-Host "2026: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "V106 Python compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "V106 failed" }
