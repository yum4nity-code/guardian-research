$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$FeatDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"
$PhaseBDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_c_v1"

function Get-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python 3 not found."
}

function Invoke-Python([string]$Script, [string[]]$Arguments) {
    $cmd = Get-PythonCommand
    $exe = $cmd[0]
    $prefix = @()
    if ($cmd.Count -gt 1) { $prefix = $cmd[1..($cmd.Count - 1)] }
    & $exe @prefix $Script @Arguments | Out-Host
    $exitCode = [int]$LASTEXITCODE
    return $exitCode
}

$Analyzer = Join-Path $PSScriptRoot "phase_c_stability_multipletest_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Summary = Join-Path $OutDir "phase_c_summary.json"
$All = Join-Path $OutDir "phase_c_all_candidates.csv"
$Passes = Join-Path $OutDir "phase_c_distinct_passes.csv"
$Clusters = Join-Path $OutDir "phase_c_dedup_clusters.csv"
$Artifacts = @($Summary,$All,$Passes,$Clusters)

Write-Host "=== PHASE C AUTONOMOUS RECOVERY V1.01 ===" -ForegroundColor Cyan

foreach ($p in @($FeatDir,$PhaseBDir)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Required directory not found: $p" }
}

$haveAll = $true
foreach ($p in $Artifacts) {
    if (-not (Test-Path -LiteralPath $p)) { $haveAll = $false }
}

if (-not $haveAll) {
    Write-Host "Phase C artifacts incomplete; rerunning analysis once..."
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $code = Invoke-Python $Analyzer @("--features-dir",$FeatDir,"--phase-b-dir",$PhaseBDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase C analysis failed, exit=$code" }
}
else {
    Write-Host "Existing Phase C artifacts found; no recomputation needed."
}

foreach ($p in $Artifacts) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Expected Phase C artifact missing after analysis: $p" }
}

$pubArgs = @(
    "--phase","phase-c-stability",
    "--status","PASS",
    "--summary","Phase C robustness screen completed or recovered and published. 2026 remains untouched."
)
foreach ($p in $Artifacts) { $pubArgs += @("--artifact",$p) }

$pubCode = Invoke-Python $Publisher $pubArgs
if ($pubCode -ne 0) { throw "Phase C publication failed, exit=$pubCode" }

Write-Host "PHASE C RECOVERY/PUBLICATION OK" -ForegroundColor Green
exit 0
