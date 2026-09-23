param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\audit_ea01_existing_oos_v2.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== EA01 V2 READ-ONLY EXISTING OOS AUDIT ==="
Write-Host "NO MARKET RERUN. NO PARAMETER SEARCH. NO 2026 ACCESS."
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "Compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "EA01 V2 audit failed" }
