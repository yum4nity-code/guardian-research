param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_m5_motion_topology_m04_validation"
if(!(Test-Path $Base)){ throw "No M04 validation run yet" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "RUN:" $Run.FullName
foreach($Name in @("PRE2018_PARITY.csv","RUN_RECEIPT.json","VALIDATION_RESULTS.csv","VALIDATION_YEARLY.csv","VALIDATION_LEAVE_ONE_YEAR_OUT.csv","VALIDATION_PLACEBO_SHIFTS.csv","FROZEN_VALIDATION_SURVIVORS.csv")){
  $P=Join-Path $Run.FullName $Name
  if(Test-Path $P){ Write-Host "`n=== $Name ==="; Get-Content $P -Raw }
}
