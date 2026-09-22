param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_edge_factory_v103_rates_preoos_forensic"
if(!(Test-Path $Base)){ throw "No V103 base directory yet: $Base" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(!$Run){ throw "No V103 run directory yet" }
Write-Host "=== V103 LATEST RUN ==="
Write-Host $Run.FullName
foreach($Name in @("LIVE_STATUS.json","RUN_RECEIPT.json")){
  $P=Join-Path $Run.FullName $Name
  if(Test-Path $P){ Write-Host "`n=== $Name ==="; Get-Content $P -Raw }
}
