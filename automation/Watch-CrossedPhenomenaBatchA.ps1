param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_crossed_batch_a_discovery"
if(!(Test-Path $Base)){ throw "No Batch A run directory yet" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(!$Run){ throw "No Batch A run directory yet" }
Write-Host "=== BATCH A LATEST RUN ==="
Write-Host $Run.FullName
foreach($Name in @("LIVE_STATUS.json","RUN_RECEIPT.json","LINEAGE_SUMMARY.csv")){
  $P=Join-Path $Run.FullName $Name
  if(Test-Path $P){ Write-Host "`n=== $Name ==="; Get-Content $P -Raw }
}
