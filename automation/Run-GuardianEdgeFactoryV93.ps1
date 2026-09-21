param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Mat=Join-Path $Repo "scripts\gef_v93_materialize_clean_oos.py"
$Eval=Join-Path $Repo "scripts\gef_v93_locked_oos_2023_2025.py"

if(!(Test-Path $Mat)){throw "Missing $Mat"}
if(!(Test-Path $Eval)){throw "Missing $Eval"}

py -m py_compile $Mat
if($LASTEXITCODE -ne 0){throw "V93 materializer compile failed"}
py -m py_compile $Eval
if($LASTEXITCODE -ne 0){throw "V93 evaluator compile failed"}

Write-Host "=== GEF V93M - MATERIALIZE ONLY MISSING FROZEN-PANEL OOS FILES ==="
py $Mat
if($LASTEXITCODE -ne 0){throw "V93 materialization failed"}

Write-Host ""
Write-Host "=== GEF V93 - LOCKED OOS 2023-2025 / FROZEN PANEL ==="
py $Eval
if($LASTEXITCODE -ne 0){throw "V93 locked OOS failed"}
