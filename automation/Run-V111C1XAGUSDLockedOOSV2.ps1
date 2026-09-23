$ErrorActionPreference="Stop"
$Root="D:\MT5_Backtests"
$Stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$Out=Join-Path $Root "Research\Autonomous\v111_c1_xagusd_locked_oos_v2\XAGC1-$Stamp"
$Zip=Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_V111_C1_XAGUSD_LOCKED_OOS_V2_$Stamp.zip"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Py=Join-Path $Root "guardian-research\scripts\gef_v111_c1_xagusd_locked_oos_v2.py"
Write-Host "=== V111-C1 XAGUSD H11 60m SHORT — LOCKED OOS V2 ===" -ForegroundColor Cyan
Write-Host "Window: 2023-2025 only | 2026 BLOCKED | NO RETUNING" -ForegroundColor Yellow
$Old=$ErrorActionPreference;$ErrorActionPreference="Continue"
py -3 $Py --root $Root --out $Out --unlock OPEN_V111_C1_XAGUSD_OOS_2023_2025 2>&1 | Tee-Object -FilePath (Join-Path $Out "RUN.log")
$Code=$LASTEXITCODE
$ErrorActionPreference=$Old
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
if($Code -eq 0){Write-Host "=== COMPLETE ===" -ForegroundColor Green}else{Write-Host "=== FAILED ===" -ForegroundColor Red}
Write-Host "ZIP: $Zip" -ForegroundColor Cyan
exit $Code
