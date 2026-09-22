param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\gef_v108_treasury_source_forensic.py"
if(!(Test-Path $Py)){ throw "Missing $Py" }
Write-Host "=== GEF V108 - TREASURY AUCTION SOURCE FORENSIC ==="
Write-Host "EDGE TRIALS: ZERO"
Write-Host "MARKET RETURNS: NOT READ"
py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "V108 Python compile failed" }
py $Py --root $Root
if($LASTEXITCODE -ne 0){ throw "V108 failed" }
