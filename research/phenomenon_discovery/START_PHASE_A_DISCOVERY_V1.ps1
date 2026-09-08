param(
    [string]$Start = "2024-01-01",
    [string]$End = "2026-01-01"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$HistDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\historical_v1"
$FeatDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python 3 not found."
}

$Python = Find-Python
$Exe = $Python[0]
$Prefix = @()
if ($Python.Count -gt 1) { $Prefix = $Python[1..($Python.Count-1)] }

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE A ===" -ForegroundColor Cyan
Write-Host "Discovery window: $Start -> $End (end exclusive)"
Write-Host "Symbols: BTCUSDT ETHUSDT"
Write-Host "2026 is intentionally NOT downloaded by this launcher."
Write-Host ""

New-Item -ItemType Directory -Force -Path $HistDir | Out-Null
New-Item -ItemType Directory -Force -Path $FeatDir | Out-Null

$Downloader = Join-Path $PSScriptRoot "download_bybit_oi_price_v1_00.py"
$Builder = Join-Path $PSScriptRoot "build_feature_matrix_v1_00.py"
$Checker = Join-Path $PSScriptRoot "check_dataset_v1_00.py"

& $Exe @Prefix $Downloader --start $Start --end $End --symbols BTCUSDT ETHUSDT --output-dir $HistDir
if ($LASTEXITCODE -ne 0) { throw "Historical download failed, exit=$LASTEXITCODE" }

& $Exe @Prefix $Builder --input-dir $HistDir --output-dir $FeatDir
if ($LASTEXITCODE -ne 0) { throw "Feature build failed, exit=$LASTEXITCODE" }

& $Exe @Prefix $Checker --historical-dir $HistDir --features-dir $FeatDir
if ($LASTEXITCODE -ne 0) { throw "Dataset integrity gate failed, exit=$LASTEXITCODE" }

Write-Host ""
Write-Host "=== PHASE A DATASET READY ===" -ForegroundColor Green
Write-Host "Historical: $HistDir"
Write-Host "Features:   $FeatDir"
Write-Host ""
Write-Host "STOP HERE. Do not download/open 2026 for discovery."
Write-Host "Send me the console output and dataset_integrity_v1.json results before Phase B."
