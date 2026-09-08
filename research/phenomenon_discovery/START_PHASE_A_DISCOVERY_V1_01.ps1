param(
    [string]$Start = "2024-01-01",
    [string]$End = "2026-01-01"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$HistDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\historical_v1"
$FeatDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python 3 not found."
}

function Invoke-PythonFile([string]$Script, [string[]]$Arguments) {
    $cmd = Find-Python
    $exe = $cmd[0]
    $prefix = @()
    if ($cmd.Count -gt 1) { $prefix = $cmd[1..($cmd.Count - 1)] }
    & $exe @prefix $Script @Arguments
    return $LASTEXITCODE
}

$Downloader = Join-Path $PSScriptRoot "download_bybit_oi_price_v1_00.py"
$Builder = Join-Path $PSScriptRoot "build_feature_matrix_v1_00.py"
$Checker = Join-Path $PSScriptRoot "check_dataset_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Integrity = Join-Path $FeatDir "dataset_integrity_v1.json"
$Manifest = Join-Path $HistDir ("manifest_{0}_{1}.json" -f $Start,$End)

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE A v1.01 ===" -ForegroundColor Cyan
Write-Host "Discovery window: $Start -> $End (end exclusive)"
Write-Host "Symbols: BTCUSDT ETHUSDT"
Write-Host ""

try {
    New-Item -ItemType Directory -Force -Path $HistDir | Out-Null
    New-Item -ItemType Directory -Force -Path $FeatDir | Out-Null

    $code = Invoke-PythonFile $Downloader @("--start",$Start,"--end",$End,"--symbols","BTCUSDT","ETHUSDT","--output-dir",$HistDir)
    if ($code -ne 0) { throw "Historical download failed, exit=$code" }

    $code = Invoke-PythonFile $Builder @("--input-dir",$HistDir,"--output-dir",$FeatDir)
    if ($code -ne 0) { throw "Feature build failed, exit=$code" }

    $code = Invoke-PythonFile $Checker @("--historical-dir",$HistDir,"--features-dir",$FeatDir)
    if ($code -ne 0) { throw "Dataset integrity gate failed, exit=$code" }

    $pubArgs = @("--phase","phase-a","--status","PASS","--summary","Phase A dataset complete and integrity gate passed.")
    if (Test-Path -LiteralPath $Integrity) { $pubArgs += @("--artifact",$Integrity) }
    if (Test-Path -LiteralPath $Manifest) { $pubArgs += @("--artifact",$Manifest) }
    $pubCode = Invoke-PythonFile $Publisher $pubArgs
    if ($pubCode -ne 0) { Write-Warning "Dataset PASS but automatic GitHub publication failed." }

    Write-Host ""
    Write-Host "=== PHASE A DATASET READY ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $pubCode = Invoke-PythonFile $Publisher @("--phase","phase-a","--status","FAIL","--summary",$message)
        if ($pubCode -ne 0) { Write-Warning "Failure publication also failed." }
    } catch {}
    exit 1
}
