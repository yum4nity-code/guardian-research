param([string]$Root="D:\MT5_Backtests")
$Base=Join-Path $Root "Research\Autonomous\guardian_edge_factory_v108_treasury_source_forensic"
if(!(Test-Path $Base)){ throw "No V108 base directory yet: $Base" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(!$Run){ throw "No V108 run directory yet" }
Write-Host "=== V108 LATEST RUN ==="
Write-Host $Run.FullName
$P=Join-Path $Run.FullName "RUN_RECEIPT.json"
if(Test-Path $P){ Get-Content $P -Raw }
