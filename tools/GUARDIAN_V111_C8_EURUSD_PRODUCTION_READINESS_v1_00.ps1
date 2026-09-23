$ErrorActionPreference = "Stop"
$Root = "D:\MT5_Backtests"
$Repo = Join-Path $Root "guardian-research"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $Root "Research\ExecutionAudit\V111_C8_EURUSD_PRODUCTION_READINESS_$Stamp"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_V111_C8_EURUSD_PRODUCTION_READINESS_$Stamp.zip"
$Py = Join-Path $Repo "tools\analyze_v111_c8_eurusd_production_readiness_v1_00.py"

New-Item -ItemType Directory -Force -Path $Out | Out-Null
Write-Host "=== V111 C8 EURUSD PRODUCTION-READINESS AUDIT ===" -ForegroundColor Cyan
Write-Host "ANALYZE-ONLY | REUSES 2023-2025 LEDGER | 2026 BLOCKED | NO RETUNING" -ForegroundColor Yellow

$Old=$ErrorActionPreference
$ErrorActionPreference="Continue"
py -3 $Py --root $Root --out $Out 2>&1 | Tee-Object -FilePath (Join-Path $Out "RUN.log")
$Code=$LASTEXITCODE
$ErrorActionPreference=$Old
if($Code -ne 0){ throw "C8 production-readiness analyzer failed." }

if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
Write-Host "=== COMPLETE ===" -ForegroundColor Green
Write-Host ("ZIP: "+$Zip) -ForegroundColor Green
