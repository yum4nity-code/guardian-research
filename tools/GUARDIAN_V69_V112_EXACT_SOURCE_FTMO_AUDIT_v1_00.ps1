$ErrorActionPreference="Stop"
$Root="D:\MT5_Backtests"
$Stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$Out=Join-Path $Root "Research\ExecutionAudit\V69_V112_EXACT_SOURCE_FTMO_$Stamp"
$Zip=Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_V69_V112_EXACT_SOURCE_FTMO_$Stamp.zip"
$Py=Join-Path $PSScriptRoot "guardian_v69_v112_exact_source_ftmo_audit_v1_00.py"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
Write-Host "=== EXACT ORIGINAL EVENTS -> FTMO EXECUTION AUDIT ===" -ForegroundColor Cyan
Write-Host "2026: BLOCKED" -ForegroundColor Yellow
Write-Host "Step 1: exact original source parity. MT5 execution is only priced if parity passes."
$Old=$ErrorActionPreference;$ErrorActionPreference="Continue"
py -3 $Py --root $Root --out $Out 2>&1 | Tee-Object -FilePath (Join-Path $Out "RUN.log")
$Code=$LASTEXITCODE
$ErrorActionPreference=$Old
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
if($Code -eq 0){Write-Host "=== COMPLETE ===" -ForegroundColor Green}else{Write-Host "=== FAILED ===" -ForegroundColor Red}
Write-Host "ZIP: $Zip" -ForegroundColor Cyan
exit $Code
