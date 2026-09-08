$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$FlowDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1"
$FeaturesDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"
$PhaseBDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1"
$PhaseCDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_c_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_fc_v1"

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

$Analyzer = Join-Path $PSScriptRoot "phase_fc_orderflow_outside_dead_regime_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"

$Summary = Join-Path $OutDir "phase_fc_summary.json"
$Audit = Join-Path $OutDir "phase_fc_filter_audit.json"
$Universe = Join-Path $OutDir "phase_fc_2024_universe.csv"
$Frozen = Join-Path $OutDir "phase_fc_frozen_shortlist_2024.csv"
$Confirm = Join-Path $OutDir "phase_fc_2025_confirmation.csv"
$Passes = Join-Path $OutDir "phase_fc_distinct_passes.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE F-C ===" -ForegroundColor Cyan
Write-Host "Order-flow outside the frozen Phase-C low-movement regime."
Write-Host "Exact 18-state Phase-C union excluded; Phase-B thresholds reused unchanged."
Write-Host "2024 discovery -> frozen shortlist -> 2025 confirmation. 2026 remains untouched."
Write-Host ""

try {
    foreach ($p in @($FlowDir,$FeaturesDir,$PhaseBDir,$PhaseCDir)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Required directory missing: $p" }
    }
    foreach ($p in @(
        (Join-Path $PhaseBDir "phase_b_summary.json"),
        (Join-Path $PhaseCDir "phase_c_distinct_passes.csv")
    )) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Required frozen prerequisite missing: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    Write-Host "Preflight: Python syntax check..."
    $code = Invoke-Python @("-m","py_compile",$Analyzer,$Publisher)
    if ($code -ne 0) { throw "Phase F-C Python preflight failed, exit=$code" }

    $code = Invoke-Python @(
        $Analyzer,
        "--flow-dir",$FlowDir,
        "--features-dir",$FeaturesDir,
        "--phase-b-dir",$PhaseBDir,
        "--phase-c-dir",$PhaseCDir,
        "--output-dir",$OutDir
    )
    if ($code -ne 0) { throw "Phase F-C conditional order-flow screen failed, exit=$code" }

    $pubArgs = @(
        $Publisher,
        "--phase","phase-fc-orderflow-active-regime",
        "--status","PASS",
        "--summary","Phase F-C conditional order-flow screen completed outside the exact frozen Phase-C low-movement union. Same F-B gates; 2024 discovery frozen before 2025 confirmation; 2026 untouched."
    )
    foreach ($p in @($Summary,$Audit,$Universe,$Frozen,$Confirm,$Passes)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase F-C passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE F-C COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-Python @(
            $Publisher,
            "--phase","phase-fc-orderflow-active-regime",
            "--status","FAIL",
            "--summary",$message
        )
    } catch {}
    exit 1
}
