$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = "D:\MT5_Backtests"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutDir = Join-Path $Root "Research\ExecutionAudit\V69_V112_$Stamp"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ZipOut = Join-Path $Desktop "GUARDIAN_V69_V112_EXECUTION_AUDIT_RESULTS_$Stamp.zip"
$PyFile = Join-Path $PSScriptRoot "guardian_v69_v112_execution_audit_v1_01.py"
$LogFile = Join-Path $OutDir "RUN.log"

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

Write-Host ""
Write-Host "=== GUARDIAN V69 / V112 EXECUTION AUDIT v1.01 ===" -ForegroundColor Cyan
Write-Host "2026: BLOCKED" -ForegroundColor Yellow
Write-Host "Output: $OutDir"

if (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"
    $Prefix = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
    $Prefix = @()
} else {
    throw "Python 3 introuvable."
}

$Check = 'import importlib.util,sys; m=[x for x in ["MetaTrader5","pandas","numpy"] if importlib.util.find_spec(x) is None]; print(",".join(m)); sys.exit(2 if m else 0)'
$Missing = & $Python @Prefix -c $Check
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installation modules: $Missing" -ForegroundColor Yellow
    & $Python @Prefix -m pip install --user MetaTrader5 pandas numpy
    if ($LASTEXITCODE -ne 0) { throw "Installation Python impossible." }
}

Write-Host ""
Write-Host "MT5 doit etre OUVERT et CONNECTE au broker." -ForegroundColor Yellow
Write-Host "Lancement..." -ForegroundColor Cyan

& $Python @Prefix $PyFile $OutDir 2>&1 | Tee-Object -FilePath $LogFile
$ExitCode = $LASTEXITCODE

if (Test-Path $ZipOut) { Remove-Item $ZipOut -Force }
Compress-Archive -Path "$OutDir\*" -DestinationPath $ZipOut -CompressionLevel Optimal -Force

Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "=== AUDIT TERMINE ===" -ForegroundColor Green
} else {
    Write-Host "=== AUDIT EN ECHEC ===" -ForegroundColor Red
}
Write-Host "ZIP: $ZipOut" -ForegroundColor Cyan
Write-Host "Envoie ce ZIP dans ChatGPT." -ForegroundColor Yellow
exit $ExitCode
