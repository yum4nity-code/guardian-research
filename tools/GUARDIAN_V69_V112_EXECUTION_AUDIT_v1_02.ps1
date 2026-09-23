$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = "D:\MT5_Backtests"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutDir = Join-Path $Root "Research\ExecutionAudit\V69_V112_$Stamp"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ZipOut = Join-Path $Desktop "GUARDIAN_V69_V112_EXECUTION_AUDIT_RESULTS_$Stamp.zip"
$PyFile = Join-Path $PSScriptRoot "guardian_v69_v112_execution_audit_v1_02.py"
$LogFile = Join-Path $OutDir "RUN.log"
$CheckFile = Join-Path $OutDir "_check_python_modules.py"

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

Write-Host ""
Write-Host "=== GUARDIAN V69 / V112 EXECUTION AUDIT v1.02 ===" -ForegroundColor Cyan
Write-Host "2026: BLOCKED" -ForegroundColor Yellow
Write-Host "FTMO ACCOUNT: REQUIRED" -ForegroundColor Yellow
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

@'
import importlib.util
import sys
mods = ["MetaTrader5", "pandas", "numpy"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
print(",".join(missing))
sys.exit(2 if missing else 0)
'@ | Set-Content -Path $CheckFile -Encoding UTF8

$OldEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$Missing = & $Python @Prefix $CheckFile 2>&1
$CheckExit = $LASTEXITCODE
$ErrorActionPreference = $OldEAP

if ($CheckExit -ne 0) {
    Write-Host "Installation modules: $Missing" -ForegroundColor Yellow
    $OldEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Python @Prefix -m pip install --user MetaTrader5 pandas numpy
    $PipExit = $LASTEXITCODE
    $ErrorActionPreference = $OldEAP
    if ($PipExit -ne 0) { throw "Installation Python impossible." }
}

Write-Host ""
Write-Host "MT5 FTMO doit etre OUVERT et CONNECTE." -ForegroundColor Yellow
Write-Host "Ferme les autres terminaux MT5 avant de continuer." -ForegroundColor Yellow
Write-Host "Lancement..." -ForegroundColor Cyan
Write-Host ""

$env:PYTHONWARNINGS = "ignore::UserWarning"
$OldEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Python @Prefix $PyFile $OutDir 2>&1 | Tee-Object -FilePath $LogFile
$ExitCode = $LASTEXITCODE
$ErrorActionPreference = $OldEAP
Remove-Item Env:PYTHONWARNINGS -ErrorAction SilentlyContinue

if (Test-Path $ZipOut) { Remove-Item $ZipOut -Force }
Compress-Archive -Path "$OutDir\*" -DestinationPath $ZipOut -CompressionLevel Optimal -Force

Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "=== AUDIT TERMINE ===" -ForegroundColor Green
} else {
    Write-Host "=== AUDIT EN ECHEC ===" -ForegroundColor Red
    Write-Host "Dernieres lignes du log:" -ForegroundColor Yellow
    Get-Content $LogFile -Tail 40 -ErrorAction SilentlyContinue
}
Write-Host ""
Write-Host "ZIP: $ZipOut" -ForegroundColor Cyan
Write-Host "Envoie ce ZIP dans ChatGPT." -ForegroundColor Yellow
exit $ExitCode
