$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$FeatDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"
$PhaseBDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_c_v1"

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
    $code = $LASTEXITCODE
    return [int]$code
}

$Analyzer = Join-Path $PSScriptRoot "phase_c_stability_multipletest_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Summary = Join-Path $OutDir "phase_c_summary.json"
$All = Join-Path $OutDir "phase_c_all_candidates.csv"
$Passes = Join-Path $OutDir "phase_c_distinct_passes.csv"
$Clusters = Join-Path $OutDir "phase_c_dedup_clusters.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE C ===" -ForegroundColor Cyan
Write-Host "Deduplication + time stability + plateau checks + multiple-testing correction."
Write-Host "2026 remains untouched. This is NOT independent validation."
Write-Host ""

try {
    foreach ($p in @($FeatDir,$PhaseBDir)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Required directory not found: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    $code = Invoke-PythonFile $Analyzer @("--features-dir",$FeatDir,"--phase-b-dir",$PhaseBDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase C analysis failed, exit=$code" }

    $pubArgs = @(
        "--phase","phase-c-stability",
        "--status","PASS",
        "--summary","Phase C robustness screen completed: deduplication, 2025 quarter stability, local quantile plateaus and multiple-testing correction. 2026 untouched."
    )
    foreach ($p in @($Summary,$All,$Passes,$Clusters)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-PythonFile $Publisher $pubArgs
    if ($pubCode -ne 0) { throw "Phase C completed but automatic GitHub publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE C COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-PythonFile $Publisher @("--phase","phase-c-stability","--status","FAIL","--summary",$message)
    } catch {}
    exit 1
}
