param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\freeze_m04_pre2018_reference.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== FREEZE M04 PRE-2018 PARITY REFERENCE ==="
Write-Host "SOURCE YEARS: 2011-2017 ONLY"
Write-Host "2018+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Pre-2018 reference compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "Pre-2018 reference build failed" }
