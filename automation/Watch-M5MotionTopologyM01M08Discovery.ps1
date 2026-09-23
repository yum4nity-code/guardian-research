param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_m5_motion_topology_m01_m08"
if(!(Test-Path $Base)){ throw "No M01-M08 discovery run yet" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "RUN:" $Run.FullName
foreach($Name in @("LIVE_STATUS.json","DISCOVERY_FREEZE_RECEIPT.json","RUN_RECEIPT.json","FAMILY_SUMMARY.csv","FROZEN_DISCOVERY_SURVIVORS.csv")){
  $P=Join-Path $Run.FullName $Name
  if(Test-Path $P){ Write-Host "`n=== $Name ==="; Get-Content $P -Raw }
}
