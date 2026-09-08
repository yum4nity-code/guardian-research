$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$InputDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\event_shock_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_hb_v1"

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python 3 not found."
}
function Invoke-Python([string[]]$Arguments) {
    $cmd = Find-Python; $exe=$cmd[0]; $prefix=@()
    if ($cmd.Count -gt 1) { $prefix=$cmd[1..($cmd.Count-1)] }
    & $exe @prefix @Arguments | Out-Host
    return [int]$LASTEXITCODE
}

$Engine = Join-Path $PSScriptRoot "phase_hb_rare_event_atlas_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Summary = Join-Path $OutDir "phase_hb_summary.json"
$Universe = Join-Path $OutDir "phase_hb_2024_universe.csv"
$Frozen = Join-Path $OutDir "phase_hb_frozen_shortlist_2024.json"
$Confirmation = Join-Path $OutDir "phase_hb_2025_confirmation.csv"
$Passes = Join-Path $OutDir "phase_hb_distinct_passes.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE H-B ===" -ForegroundColor Cyan
Write-Host "Rare-event atlas: 1%-2% shock tails, five horizons, three path outcomes."
Write-Host "Chronology: 2024 discovery/freeze -> 2025 confirmation. 2026 remains untouched."
Write-Host "Prop-firm tradability remains fail-closed until historical news masking is applied."
Write-Host ""

try {
    if (-not (Test-Path -LiteralPath $InputDir)) { throw "Required H-A input directory missing: $InputDir" }
    foreach ($sym in @("BTCUSDT","ETHUSDT")) {
        $p = Join-Path $InputDir ($sym + "_event_shock_matrix_2024-01-01_2026-01-01.csv")
        if (-not (Test-Path -LiteralPath $p)) { throw "Required H-A matrix missing: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $code=Invoke-Python @("-m","py_compile",$Engine,$Publisher)
    if ($code -ne 0) { throw "Phase H-B Python preflight failed, exit=$code" }
    $code=Invoke-Python @($Engine,"--input-dir",$InputDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase H-B analysis failed, exit=$code" }
    if (-not (Test-Path -LiteralPath $Summary)) { throw "Phase H-B summary missing after analysis." }

    $pubArgs=@($Publisher,"--phase","phase-hb-rare-event-atlas","--status","PASS","--summary","Phase H-B rare-event atlas completed. 1%-2% shock tails tested across 15m/30m/1h/2h/4h; 2024 discovery frozen before 2025 read; 2026 untouched; no candidate is prop-firm tradable until historical news masking is applied.")
    foreach ($p in @($Summary,$Universe,$Frozen,$Confirmation,$Passes)) { if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) } }
    $pubCode=Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase H-B passed locally but publication failed, exit=$pubCode" }
    Write-Host ""
    Write-Host "=== PHASE H-B COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message=$_.Exception.Message; Write-Error $message
    try { $null=Invoke-Python @($Publisher,"--phase","phase-hb-rare-event-atlas","--status","FAIL","--summary",$message) } catch {}
    exit 1
}
