$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DerivativeDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1"
$FlowDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_g_v1"

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

$Analyzer = Join-Path $PSScriptRoot "phase_g_stable_marginal_ensemble_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"

$Summary = Join-Path $OutDir "phase_g_summary.json"
$Model = Join-Path $OutDir "phase_g_frozen_model_2024.json"
$Audit = Join-Path $OutDir "phase_g_2024_contribution_audit.csv"
$Confirm = Join-Path $OutDir "phase_g_2025_confirmation.csv"
$Passes = Join-Path $OutDir "phase_g_distinct_passes.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE G ===" -ForegroundColor Cyan
Write-Host "Stable marginal evidence ensemble."
Write-Host "2024 learns only cross-asset + H1/H2 stable quintile signs."
Write-Host "Frozen model is written and hashed BEFORE 2025 is read."
Write-Host "2025 confirms or rejects. No PnL. 2026 remains untouched."
Write-Host ""

try {
    foreach ($p in @($DerivativeDir,$FlowDir)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Required directory missing: $p" }
    }
    foreach ($symbol in @("BTCUSDT","ETHUSDT")) {
        $d = Join-Path $DerivativeDir "$symbol`_derivative_context_features_v1.csv"
        $f = Join-Path $FlowDir "$symbol`_binance_spot_um_5m_orderflow_2024-01-01_2026-01-01.csv"
        if (-not (Test-Path -LiteralPath $d)) { throw "Missing derivative matrix: $d" }
        if (-not (Test-Path -LiteralPath $f)) { throw "Missing order-flow matrix: $f" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    Write-Host "Preflight: Python syntax check..."
    $code = Invoke-Python @("-m","py_compile",$Analyzer,$Publisher)
    if ($code -ne 0) { throw "Phase G Python preflight failed, exit=$code" }

    $code = Invoke-Python @(
        $Analyzer,
        "--derivative-dir",$DerivativeDir,
        "--flow-dir",$FlowDir,
        "--output-dir",$OutDir
    )
    if ($code -ne 0) { throw "Phase G ensemble analysis failed, exit=$code" }

    $pubArgs = @(
        $Publisher,
        "--phase","phase-g-stable-ensemble",
        "--status","PASS",
        "--summary","Phase G stable-marginal ensemble completed. Model learned from 2024 only and frozen before 2025 read; 2025 confirmation executed; 2026 untouched; no PnL optimization."
    )
    foreach ($p in @($Summary,$Model,$Audit,$Confirm,$Passes)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase G passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE G COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-Python @(
            $Publisher,
            "--phase","phase-g-stable-ensemble",
            "--status","FAIL",
            "--summary",$message
        )
    } catch {}
    exit 1
}
