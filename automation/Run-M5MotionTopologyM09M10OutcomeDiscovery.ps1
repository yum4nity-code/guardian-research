param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_m5_motion_topology_m09_m10_outcome_discovery.py"

if(!(Test-Path $Py)){ throw "Missing $Py" }

$dupe = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and $_.CommandLine -like "*gef_m5_motion_topology_m09_m10_outcome_discovery.py*"
}
if($dupe){ throw "M09-M10 outcome discovery already appears to be running. Refusing duplicate." }

Write-Host "=== GUARDIAN M5 M09-M10 OUTCOME DISCOVERY ===" -ForegroundColor Cyan
Write-Host "FROZEN CENSUS: GEFM5MC-20260927-100900"
Write-Host "M09 SHA: f4b16ed02534ada03aee9acbbcfb42c9450524c54cd17065a281aacb5b3d0e80"
Write-Host "M10 SHA: 5df682a7a81d02ca9e72439e8e86434ccdf6579c0f16958316853c38729e1893"
Write-Host "DISCOVERY OUTCOMES: 2012-2014 ONLY"
Write-Host "2015+: FORBIDDEN | 2023-2025: LOCKED | 2026: FORBIDDEN"

py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "M09-M10 outcome discovery compile failed" }

py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "M09-M10 outcome discovery failed" }
