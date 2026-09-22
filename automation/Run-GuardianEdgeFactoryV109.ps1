param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_v109_treasury_event_level.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GEF V109 - TREASURY AUCTION EVENT-LEVEL ==="
Write-Host "STATISTICAL UNIT: ONE AUCTION"
Write-Host "2023-2025: FORBIDDEN"
Write-Host "2026+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "V109 Python compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "V109 failed" }
