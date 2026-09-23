param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_m5_motion_topology_m04_locked_oos"
if(!(Test-Path $Base)){ throw "No M04 locked OOS run yet" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "RUN:" $Run.FullName
foreach($Name in @("PRE2023_PARITY.csv","RUN_RECEIPT.json","LOCKED_OOS_RESULTS.csv","LOCKED_OOS_YEARLY.csv","LOCKED_OOS_LEAVE_ONE_YEAR_OUT.csv","LOCKED_OOS_PLACEBO_SHIFTS.csv")){
  $P=Join-Path $Run.FullName $Name
  if(Test-Path $P){ Write-Host "`n=== $Name ==="; Get-Content $P -Raw }
}
