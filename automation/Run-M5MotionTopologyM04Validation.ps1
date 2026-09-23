param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_m5_motion_topology_m04_validation.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN M5 M04 2018-2022 VALIDATION ==="
Write-Host "FROZEN VARIANTS: 5"
Write-Host "REQUIRES FROZEN PRE-2018 REFERENCE"
Write-Host "RAW HISTORY: 2011-2022"
Write-Host "VALIDATION: 2018-2022"
Write-Host "2023+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M04 validation compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M04 validation failed" }
