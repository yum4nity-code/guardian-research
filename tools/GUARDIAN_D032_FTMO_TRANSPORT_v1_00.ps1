$ErrorActionPreference = "Stop"
$Root = "D:\MT5_Backtests"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $Root "Research\ExecutionAudit\D032_FTMO_TRANSPORT_$Stamp"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_D032_FTMO_TRANSPORT_$Stamp.zip"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Py = Join-Path $Root "guardian-research\tools\guardian_d032_ftmo_transport_v1_00.py"
Write-Host "=== D032 BULLISH DOJI STAR H1 - FTMO TRANSPORT ===" -ForegroundColor Cyan
Write-Host "Frozen signal | +24h endpoint | 2026 BLOCKED | NO RETUNING" -ForegroundColor Yellow
$Old = $ErrorActionPreference
$ErrorActionPreference = "Continue"
py -3 $Py --out $Out 2>&1 | Tee-Object -FilePath (Join-Path $Out "RUN.log")
$Code = $LASTEXITCODE
$ErrorActionPreference = $Old
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
if ($Code -eq 0) { Write-Host "=== COMPLETE ===" -ForegroundColor Green } else { Write-Host "=== FAILED ===" -ForegroundColor Red }
Write-Host "ZIP: $Zip" -ForegroundColor Cyan
exit $Code
