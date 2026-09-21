param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_v91_materialize_xagusd_2023_2025.py"
$V91=Join-Path $Repo "automation\Run-GuardianEdgeFactoryV91.ps1"

if(!(Test-Path $Py)){throw "Missing $Py"}
if(!(Test-Path $V91)){throw "Missing $V91"}

py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V91 materializer compile failed"}

Write-Host "=== GEF V91M - MATERIALIZE XAGUSD 2023-2025 ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V91 XAG materialization failed"}

$Latest = Get-ChildItem (Join-Path $Root "Research\Autonomous\guardian_edge_factory_v91_materialize\GEF91M-*") -Directory |
  Sort-Object Name -Descending | Select-Object -First 1
if(!$Latest){throw "No V91M output directory found"}
$Receipt = Get-Content (Join-Path $Latest.FullName "RUN_RECEIPT.json") -Raw | ConvertFrom-Json
if($Receipt.status -ne "COMPLETE_XAGUSD_2023_2025_MATERIALIZATION"){
  throw "V91M did not complete cleanly: $($Receipt.status)"
}

Write-Host ""
Write-Host "=== MATERIALIZATION COMPLETE - RETRYING FROZEN V91 ==="
powershell -ExecutionPolicy Bypass -File $V91
if($LASTEXITCODE -ne 0){throw "Frozen V91 retry failed"}
