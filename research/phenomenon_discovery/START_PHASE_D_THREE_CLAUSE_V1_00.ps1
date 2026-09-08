$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$FeatDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"
$PhaseBDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_d_v1"

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

$Analyzer = Join-Path $PSScriptRoot "phase_d_three_clause_directional_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Summary = Join-Path $OutDir "phase_d_summary.json"
$Universe = Join-Path $OutDir "phase_d_2024_full_universe.csv"
$Frozen = Join-Path $OutDir "phase_d_frozen_shortlist_2024.csv"
$Confirm = Join-Path $OutDir "phase_d_2025_confirmation.csv"
$Passes = Join-Path $OutDir "phase_d_distinct_passes.csv"
$Clusters = Join-Path $OutDir "phase_d_dedup_clusters.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE D ===" -ForegroundColor Cyan
Write-Host "Exhaustive deterministic 3-clause directional discovery."
Write-Host "2024 generates and freezes candidates; 2025 confirms; 2026 remains untouched."
Write-Host "No PnL optimization."
Write-Host ""

try {
    foreach ($p in @($FeatDir,$PhaseBDir)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Required directory not found: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    $code = Invoke-PythonFile $Analyzer @("--features-dir",$FeatDir,"--phase-b-dir",$PhaseBDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase D analysis failed, exit=$code" }

    $pubArgs = @(
        "--phase","phase-d-three-clause",
        "--status","PASS",
        "--summary","Phase D deterministic 3-clause directional search completed. 2024 candidate generation frozen before 2025 confirmation; 2026 untouched."
    )
    foreach ($p in @($Summary,$Universe,$Frozen,$Confirm,$Passes,$Clusters)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-PythonFile $Publisher $pubArgs
    if ($pubCode -ne 0) { throw "Phase D completed but automatic GitHub publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE D COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-PythonFile $Publisher @("--phase","phase-d-three-clause","--status","FAIL","--summary",$message)
    } catch {}
    exit 1
}
