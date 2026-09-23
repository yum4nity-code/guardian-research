param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_m5_motion_topology_m04_replication"
if(!(Test-Path $Base)){ throw "No M04 replication run yet" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "RUN:" $Run.FullName
foreach($Name in @("LIVE_STATUS.json","PRE2015_PARITY.csv","RUN_RECEIPT.json","REPLICATION_RESULTS.csv","REPLICATION_YEARLY.csv","FROZEN_REPLICATION_SURVIVORS.csv")){
  $P=Join-Path $Run.FullName $Name
  if(Test-Path $P){ Write-Host "`n=== $Name ==="; Get-Content $P -Raw }
}
