$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ContextDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_context_v1"
$MatrixDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1"
$FeaturesDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"

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
    & $exe @prefix $Script @Arguments | Out-Host
    return [int]$LASTEXITCODE
}

function Test-CompleteDownloads {
    $manifest = Join-Path $ContextDir "manifest_derivative_2024-01-01_2026-01-01.json"
    if (-not (Test-Path -LiteralPath $manifest)) { return $false }
    foreach ($symbol in @("BTCUSDT","ETHUSDT")) {
        $ctx = @(Get-ChildItem -LiteralPath $ContextDir -Filter "$symbol`_bybit_derivative_5m_*.csv" -File -ErrorAction SilentlyContinue)
        $fund = @(Get-ChildItem -LiteralPath $ContextDir -Filter "$symbol`_bybit_funding_*.csv" -File -ErrorAction SilentlyContinue)
        if ($ctx.Count -ne 1 -or $fund.Count -ne 1) { return $false }
    }
    return $true
}

$Downloader = Join-Path $PSScriptRoot "download_bybit_derivative_context_v1_00.py"
$Builder = Join-Path $PSScriptRoot "build_derivative_context_matrix_v1_01.py"
$Checker = Join-Path $PSScriptRoot "check_derivative_context_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"

$DownloadManifest = Join-Path $ContextDir "manifest_derivative_2024-01-01_2026-01-01.json"
$MatrixManifest = Join-Path $MatrixDir "derivative_matrix_manifest_v1.json"
$Integrity = Join-Path $MatrixDir "derivative_context_integrity_v1.json"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE E-A V1.01 ===" -ForegroundColor Cyan
Write-Host "Derivative context dataset only: mark/index/premium/funding."
Write-Host "2024-2025 only. 2026 remains untouched. No rule search in this phase."
Write-Host ""

try {
    New-Item -ItemType Directory -Force -Path $ContextDir | Out-Null
    New-Item -ItemType Directory -Force -Path $MatrixDir | Out-Null

    if (Test-CompleteDownloads) {
        Write-Host "Complete derivative downloads already present. Reusing them."
    } else {
        $code = Invoke-PythonFile $Downloader @(
            "--start","2024-01-01",
            "--end","2026-01-01",
            "--symbols","BTCUSDT","ETHUSDT",
            "--output-dir",$ContextDir
        )
        if ($code -ne 0) { throw "Phase E-A derivative download failed, exit=$code" }
    }

    $code = Invoke-PythonFile $Builder @(
        "--features-dir",$FeaturesDir,
        "--context-dir",$ContextDir,
        "--output-dir",$MatrixDir
    )
    if ($code -ne 0) { throw "Phase E-A v1.01 matrix build failed, exit=$code" }

    $code = Invoke-PythonFile $Checker @(
        "--context-dir",$ContextDir,
        "--matrix-dir",$MatrixDir
    )
    if ($code -ne 0) { throw "Phase E-A integrity gate failed, exit=$code" }

    $pubArgs = @(
        "--phase","phase-ea-derivative-context",
        "--status","PASS",
        "--summary","Phase E-A v1.01 derivative context gate passed. Complete downloads reused when available; causal as-of settled funding built for 2024-2025 only; 2026 untouched; no rule search executed."
    )
    foreach ($p in @($DownloadManifest,$MatrixManifest,$Integrity)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-PythonFile $Publisher $pubArgs
    if ($pubCode -ne 0) { throw "Phase E-A passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE E-A V1.01 DATASET COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-PythonFile $Publisher @(
            "--phase","phase-ea-derivative-context",
            "--status","FAIL",
            "--summary",$message
        )
    } catch {}
    exit 1
}
