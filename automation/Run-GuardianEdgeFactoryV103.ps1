param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_v103_rates_preoos_forensic.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GEF V103 - V102 FINAL PRE-OOS FORENSIC ==="
Write-Host "2023-2025: FORBIDDEN"
Write-Host "2026+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "V103 Python compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "V103 failed" }
