$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ContextDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_context_v1"
$MatrixDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1"

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

$Downloader = Join-Path $PSScriptRoot "download_bybit_derivative_context_v1_00.py"
$Builder = Join-Path $PSScriptRoot "build_derivative_context_matrix_v1_00.py"
$Checker = Join-Path $PSScriptRoot "check_derivative_context_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"

$DownloadManifest = Join-Path $ContextDir "manifest_derivative_2024-01-01_2026-01-01.json"
$MatrixManifest = Join-Path $MatrixDir "derivative_matrix_manifest_v1.json"
$Integrity = Join-Path $MatrixDir "derivative_context_integrity_v1.json"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE E-A ===" -ForegroundColor Cyan
Write-Host "Derivative context dataset only: mark/index/premium/funding."
Write-Host "2024-2025 only. 2026 remains untouched. No rule search in this phase."
Write-Host ""

try {
    New-Item -ItemType Directory -Force -Path $ContextDir | Out-Null
    New-Item -ItemType Directory -Force -Path $MatrixDir | Out-Null

    $code = Invoke-PythonFile $Downloader @(
        "--start","2024-01-01",
        "--end","2026-01-01",
        "--symbols","BTCUSDT","ETHUSDT",
        "--output-dir",$ContextDir
    )
    if ($code -ne 0) { throw "Phase E-A derivative download failed, exit=$code" }

    $code = Invoke-PythonFile $Builder @(
        "--features-dir","D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1",
        "--context-dir",$ContextDir,
        "--output-dir",$MatrixDir
    )
    if ($code -ne 0) { throw "Phase E-A matrix build failed, exit=$code" }

    $code = Invoke-PythonFile $Checker @(
        "--context-dir",$ContextDir,
        "--matrix-dir",$MatrixDir
    )
    if ($code -ne 0) { throw "Phase E-A integrity gate failed, exit=$code" }

    $pubArgs = @(
        "--phase","phase-ea-derivative-context",
        "--status","PASS",
        "--summary","Phase E-A derivative context gate passed. Mark/index/premium and causal as-of settled funding built for 2024-2025 only; 2026 untouched. No rule search executed."
    )
    foreach ($p in @($DownloadManifest,$MatrixManifest,$Integrity)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-PythonFile $Publisher $pubArgs
    if ($pubCode -ne 0) { throw "Phase E-A passed locally but automatic GitHub publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE E-A DATASET COMPLETE AND PUBLISHED ===" -ForegroundColor Green
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
