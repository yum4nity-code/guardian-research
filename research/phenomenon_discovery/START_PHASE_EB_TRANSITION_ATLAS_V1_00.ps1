$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$MatrixDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_eb_v1"

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python 3 not found."
}

function Invoke-Python([string[]]$Arguments) {
    $cmd = Find-Python
    $exe = $cmd[0]
    $prefix = @()
    if ($cmd.Count -gt 1) { $prefix = $cmd[1..($cmd.Count - 1)] }
    & $exe @prefix @Arguments | Out-Host
    return [int]$LASTEXITCODE
}

$Analyzer = Join-Path $PSScriptRoot "phase_eb_transition_atlas_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"

$Summary = Join-Path $OutDir "phase_eb_summary.json"
$Universe = Join-Path $OutDir "phase_eb_2024_transition_universe.csv"
$Frozen = Join-Path $OutDir "phase_eb_frozen_shortlist_2024.csv"
$Confirm = Join-Path $OutDir "phase_eb_2025_confirmation.csv"
$Passes = Join-Path $OutDir "phase_eb_distinct_passes.csv"
$Clusters = Join-Path $OutDir "phase_eb_dedup_clusters.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE E-B ===" -ForegroundColor Cyan
Write-Host "Single-variable derivative/OI transition atlas."
Write-Host "2024 discovery -> frozen shortlist -> 2025 confirmation."
Write-Host "No transition combinations. No PnL optimization. 2026 remains untouched."
Write-Host ""

try {
    if (-not (Test-Path -LiteralPath $MatrixDir)) {
        throw "Phase E-A matrix directory not found: $MatrixDir"
    }
    foreach ($symbol in @("BTCUSDT","ETHUSDT")) {
        $matrix = Join-Path $MatrixDir "$symbol`_derivative_context_features_v1.csv"
        if (-not (Test-Path -LiteralPath $matrix)) {
            throw "Missing Phase E-A matrix: $matrix"
        }
    }

    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    Write-Host "Preflight: Python syntax check..."
    $code = Invoke-Python @("-m","py_compile",$Analyzer,$Publisher)
    if ($code -ne 0) { throw "Phase E-B Python preflight failed, exit=$code" }

    $code = Invoke-Python @($Analyzer,"--matrix-dir",$MatrixDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase E-B transition atlas failed, exit=$code" }

    $pubArgs = @(
        $Publisher,
        "--phase","phase-eb-transition-atlas",
        "--status","PASS",
        "--summary","Phase E-B single-variable transition atlas completed. 2024 discovery frozen before 2025 confirmation; no transition combinations; 2026 untouched."
    )
    foreach ($p in @($Summary,$Universe,$Frozen,$Confirm,$Passes,$Clusters)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase E-B passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE E-B COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-Python @(
            $Publisher,
            "--phase","phase-eb-transition-atlas",
            "--status","FAIL",
            "--summary",$message
        )
    } catch {}
    exit 1
}
