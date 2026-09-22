param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_edge_factory_v102_standalone_rates"
if(!(Test-Path $Base)){ throw "No V102 base directory yet: $Base" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(!$Run){ throw "No V102 run directory yet" }
Write-Host "=== V102 LATEST RUN ==="
Write-Host $Run.FullName
$Status=Join-Path $Run.FullName "LIVE_STATUS.json"
$Receipt=Join-Path $Run.FullName "RUN_RECEIPT.json"
if(Test-Path $Status){ Write-Host "`n=== LIVE STATUS ==="; Get-Content $Status -Raw }
if(Test-Path $Receipt){ Write-Host "`n=== RECEIPT ==="; Get-Content $Receipt -Raw }
