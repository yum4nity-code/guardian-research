$ErrorActionPreference = "Stop"
$Root = "D:\MT5_Backtests"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $Root "Research\ExecutionAudit\V111_C1_XAGUSD_FTMO_$Stamp"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_V111_C1_XAGUSD_FTMO_EXECUTION_$Stamp.zip"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Py = Join-Path $Root "guardian-research\tools\guardian_v111_c1_xagusd_ftmo_execution_audit_v1_00.py"

Write-Host "=== V111-C1 XAGUSD FTMO EXECUTION AUDIT ===" -ForegroundColor Cyan
Write-Host "Source frozen | Alignment by price proximity only | 2026 BLOCKED" -ForegroundColor Yellow

$Old = $ErrorActionPreference
$ErrorActionPreference = "Continue"
py -3 $Py --root $Root --out $Out 2>&1 | Tee-Object -FilePath (Join-Path $Out "RUN.log")
$Code = $LASTEXITCODE
$ErrorActionPreference = $Old

if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal -Force

if ($Code -eq 0) {
    Write-Host "=== COMPLETE ===" -ForegroundColor Green
} else {
    Write-Host "=== FAILED ===" -ForegroundColor Red
}
Write-Host "ZIP: $Zip" -ForegroundColor Cyan
exit $Code
