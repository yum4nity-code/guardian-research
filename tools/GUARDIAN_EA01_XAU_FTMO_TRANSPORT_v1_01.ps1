$ErrorActionPreference = "Stop"
$Root = "D:\MT5_Backtests"
$Repo = Join-Path $Root "guardian-research"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $Root "Research\ExecutionAudit\EA01_XR_RSI_LONG_FTMO_DST_$Stamp"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_EA01_XAU_FTMO_TRANSPORT_DST_$Stamp.zip"
$Py = Join-Path $Repo "tools\analyze_ea01_xr_rsi_long_ftmo_transport_v1_01.py"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
Write-Host "=== EA01 XAU FTMO EXECUTION TRANSPORT v1.01 DST ===" -ForegroundColor Cyan
Write-Host "Deterministic FTMO GMT+2/GMT+3 | 2023-2025 only | 2026 BLOCKED | NO RETUNING" -ForegroundColor Yellow
$Old=$ErrorActionPreference
$ErrorActionPreference="Continue"
py -3 $Py --root $Root --out $Out 2>&1 | Tee-Object -FilePath (Join-Path $Out "RUN.log")
$Code=$LASTEXITCODE
$ErrorActionPreference=$Old
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
if($Code -ne 0){
  Write-Host "=== FAILED CLOSED ===" -ForegroundColor Red
  Write-Host ("ZIP: "+$Zip) -ForegroundColor Yellow
  exit $Code
}
Write-Host "=== COMPLETE ===" -ForegroundColor Green
Write-Host ("ZIP: "+$Zip) -ForegroundColor Green
