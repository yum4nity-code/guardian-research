param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_m5_motion_topology_m04_locked_oos.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN M5 M04 LOCKED OOS 2023-2025 ==="
Write-Host "FROZEN CANDIDATES: EURUSD L15, AUDUSD L15"
Write-Host "REQUIRES FROZEN PRE-2023 REFERENCE"
Write-Host "2026: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M04 locked OOS compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M04 locked OOS failed" }
