$ErrorActionPreference="Stop"
$Root="D:\MT5_Backtests"
$Stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$Out=Join-Path $Root "Research\ExecutionAudit\V69_V112_SESSION_ALIGNED_$Stamp"
$Zip=Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_V69_V112_SESSION_ALIGNED_$Stamp.zip"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Py=Join-Path $PSScriptRoot "guardian_v69_v112_session_aligned_execution_audit_v1_01.py"
Write-Host "=== SESSION-ALIGNED EXECUTION AUDIT v1.01 ===" -ForegroundColor Cyan
Write-Host "2026: BLOCKED" -ForegroundColor Yellow
$Old=$ErrorActionPreference;$ErrorActionPreference="Continue"
py -3 $Py --root $Root --out $Out 2>&1 | Tee-Object -FilePath (Join-Path $Out "RUN.log")
$Code=$LASTEXITCODE
$ErrorActionPreference=$Old
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
if($Code -eq 0){Write-Host "=== COMPLETE ===" -ForegroundColor Green}else{Write-Host "=== FAILED ===" -ForegroundColor Red}
Write-Host "ZIP: $Zip" -ForegroundColor Cyan
exit $Code
