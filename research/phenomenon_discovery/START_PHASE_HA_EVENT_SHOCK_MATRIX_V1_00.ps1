$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$FeaturesDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"
$DerivativeDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1"
$FlowDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\event_shock_v1"

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

$Builder = Join-Path $PSScriptRoot "build_event_shock_matrix_v1_00.py"
$Checker = Join-Path $PSScriptRoot "check_event_shock_matrix_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Manifest = Join-Path $OutDir "event_shock_manifest_v1.json"
$Integrity = Join-Path $OutDir "event_shock_integrity_v1.json"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE H-A ===" -ForegroundColor Cyan
Write-Host "Rare-event shock matrix. Dataset + integrity only. No rule search."
Write-Host "Horizons: 15m / 30m / 1h / 2h / 4h. 2026 remains untouched."
Write-Host "Prop-firm promotion is fail-closed until a historical news mask is applied."
Write-Host ""

try {
    foreach ($p in @($FeaturesDir,$DerivativeDir,$FlowDir)) { if (-not (Test-Path -LiteralPath $p)) { throw "Required input directory missing: $p" } }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $code=Invoke-Python @("-m","py_compile",$Builder,$Checker,$Publisher)
    if ($code -ne 0) { throw "Phase H-A Python preflight failed, exit=$code" }
    $code=Invoke-Python @($Builder,"--features-dir",$FeaturesDir,"--derivative-dir",$DerivativeDir,"--flow-dir",$FlowDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase H-A build failed, exit=$code" }
    $code=Invoke-Python @($Checker,"--input-dir",$OutDir)
    if ($code -ne 0) { throw "Phase H-A integrity gate failed, exit=$code" }
    $pubArgs=@($Publisher,"--phase","phase-ha-event-shock-matrix","--status","PASS","--summary","Phase H-A event-shock matrix passed integrity. Multi-source rare-event predictors plus 15m/30m/1h/2h/4h path labels; 2026 untouched; prop-firm tradability remains unauthorized until historical news masking is applied.")
    foreach ($p in @($Manifest,$Integrity)) { if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) } }
    $pubCode=Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase H-A passed locally but publication failed, exit=$pubCode" }
    Write-Host ""
    Write-Host "=== PHASE H-A COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message=$_.Exception.Message; Write-Error $message
    try { $null=Invoke-Python @($Publisher,"--phase","phase-ha-event-shock-matrix","--status","FAIL","--summary",$message) } catch {}
    exit 1
}
