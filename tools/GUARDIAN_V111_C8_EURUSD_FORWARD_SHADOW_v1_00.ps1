$ErrorActionPreference = "Stop"
$Root="D:\MT5_Backtests"
$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "tools\v111_c8_eurusd_forward_shadow_v1_00.py"

$tomorrow=(Get-Date).ToUniversalTime().Date.AddDays(1).ToString("yyyy-MM-dd")
Write-Host "=== V111 C8 EURUSD FORWARD SHADOW ===" -ForegroundColor Cyan
Write-Host ("Forward-only start UTC: "+$tomorrow) -ForegroundColor Green
Write-Host "NO LIVE ORDERS | NO HISTORICAL BACKFILL | 2026 PAST DATA NOT OPENED" -ForegroundColor Yellow
Write-Host "Close this window to stop the shadow monitor." -ForegroundColor Yellow

py -3 $Py --root $Root --start-date $tomorrow --poll-seconds 15
