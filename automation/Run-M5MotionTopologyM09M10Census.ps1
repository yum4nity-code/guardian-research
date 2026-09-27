param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_m5_motion_topology_m09_m10_census.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }

$dupe = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and $_.CommandLine -like "*gef_m5_motion_topology_m09_m10_census.py*"
}
if($dupe){ throw "M09-M10 census already appears to be running. Refusing duplicate." }

Write-Host "=== GUARDIAN M5 MOTION TOPOLOGY M09-M10 MOTIF CENSUS ===" -ForegroundColor Cyan
Write-Host "PREDICTOR STATES ONLY: 2012-2014"
Write-Host "OUTCOME/TARGET FILES: NOT OPENED"
Write-Host "2015+: FORBIDDEN"
Write-Host "2023-2025: NOT ACCESSED | 2026: FORBIDDEN"

py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M09-M10 census compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M09-M10 census failed" }
