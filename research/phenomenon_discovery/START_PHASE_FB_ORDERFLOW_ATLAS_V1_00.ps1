$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$FlowDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1"
$FeatDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_fb_v1"

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

$Analyzer = Join-Path $PSScriptRoot "phase_fb_orderflow_atlas_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Summary = Join-Path $OutDir "phase_fb_summary.json"
$Universe = Join-Path $OutDir "phase_fb_2024_universe.csv"
$Frozen = Join-Path $OutDir "phase_fb_frozen_shortlist_2024.csv"
$Confirm = Join-Path $OutDir "phase_fb_2025_confirmation.csv"
$Passes = Join-Path $OutDir "phase_fb_distinct_passes.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE F-B ===" -ForegroundColor Cyan
Write-Host "Univariate Binance spot/perp aggressive-flow atlas."
Write-Host "2024 discovery -> frozen shortlist -> 2025 confirmation."
Write-Host "No combinations. No PnL optimization. 2026 remains untouched."
Write-Host ""

try {
    foreach ($p in @($FlowDir,$FeatDir)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Required directory not found: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    Write-Host "Preflight: Python syntax check..."
    $code = Invoke-Python @("-m","py_compile",$Analyzer,$Publisher)
    if ($code -ne 0) { throw "Phase F-B Python preflight failed, exit=$code" }

    $code = Invoke-Python @($Analyzer,"--flow-dir",$FlowDir,"--features-dir",$FeatDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase F-B order-flow atlas failed, exit=$code" }

    $pubArgs = @(
        $Publisher,
        "--phase","phase-fb-orderflow-atlas",
        "--status","PASS",
        "--summary","Phase F-B univariate Binance spot/perp aggressive-flow atlas completed. 2024 discovery frozen before 2025 confirmation; no feature combinations; 2026 untouched."
    )
    foreach ($p in @($Summary,$Universe,$Frozen,$Confirm,$Passes)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase F-B passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE F-B COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-Python @($Publisher,"--phase","phase-fb-orderflow-atlas","--status","FAIL","--summary",$message)
    } catch {}
    exit 1
}
