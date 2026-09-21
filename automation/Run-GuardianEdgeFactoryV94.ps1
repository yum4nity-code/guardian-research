param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v94_promote_and_freeze_2026.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V94 compile failed"}
Write-Host "=== GEF V94 - PROMOTE V93 PASSES + FREEZE 2026 FORWARD PANEL ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V94 failed"}
