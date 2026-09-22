param(
  [string]$Root="D:\MT5_Backtests",
  [string]$Unlock=""
)
$ErrorActionPreference="Stop"
if($Unlock -ne "OPEN_LOCKED_OOS_2023_2025"){
  Write-Host "V112 is preregistered but LOCKED."
  Write-Host "No 2023-2025 market file was read."
  Write-Host "To execute after human approval, pass:"
  Write-Host '-Unlock OPEN_LOCKED_OOS_2023_2025'
  exit 0
}
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_v112_calendar_locked_oos.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GEF V112 - LOCKED OOS 2023-2025 ==="
Write-Host "FROZEN CANDIDATES: 3"
Write-Host "FROZEN STRUCTURAL FAMILIES: 2"
Write-Host "2026+: FORBIDDEN"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "V112 Python compile failed" }
py $Py --root $Root --unlock OPEN_LOCKED_OOS_2023_2025
if($LASTEXITCODE -ne 0){ throw "V112 failed" }
