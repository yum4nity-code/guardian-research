param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\freeze_m04_pre2023_reference.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== FREEZE M04 PRE-2023 LOCKED-OOS REFERENCE ==="
Write-Host "SOURCE YEARS: 2011-2022 ONLY"
Write-Host "2023+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Pre-2023 reference compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "Pre-2023 reference build failed" }
