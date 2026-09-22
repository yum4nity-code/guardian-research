param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_v110_utc_calendar_structure.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GEF V110 - UTC INTRADAY/CALENDAR STRUCTURE ==="
Write-Host "UNIT: ONE TOP-OF-HOUR EVENT"
Write-Host "2023-2025: FORBIDDEN"
Write-Host "2026+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "V110 Python compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "V110 failed" }
