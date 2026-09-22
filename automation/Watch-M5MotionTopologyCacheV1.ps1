param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_m5_motion_topology_v1"
if(!(Test-Path $Base)){ throw "No M5 topology run directory yet" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "RUN:" $Run.FullName
foreach($Name in @("LIVE_STATUS.json","RUN_RECEIPT.json","CACHE_MANIFEST.json","MARKET_COVERAGE.csv","ENDPOINT_SUPPORT.csv")){
  $P=Join-Path $Run.FullName $Name
  if(Test-Path $P){ Write-Host "`n=== $Name ==="; Get-Content $P -Raw }
}
