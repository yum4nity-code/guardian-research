param(
  [string]$Root="D:\MT5_Backtests"
)
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\extract_guardian_mini_edge_audit.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GUARDIAN MINI-EDGE LOCAL RESULT EXTRACTOR ==="
Write-Host "READ-ONLY SCAN. NO BACKTEST. NO MARKET-DATA MODIFICATION."
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Extractor compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "Extractor failed" }
