$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$FeatDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"
$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1"

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
    return $LASTEXITCODE
}

$Atlas = Join-Path $PSScriptRoot "build_phenomenon_atlas_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Summary = Join-Path $OutDir "phase_b_summary.json"
$Shortlist = Join-Path $OutDir "phase_b_shortlist_and_confirmation.csv"
$Survivors = Join-Path $OutDir "phase_b_survivors.csv"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE B ATLAS ===" -ForegroundColor Cyan
Write-Host "2024 = discovery; 2025 = internal confirmation; 2026 remains untouched."
Write-Host "No PnL optimization. No trading rules."
Write-Host ""

try {
    if (-not (Test-Path -LiteralPath $FeatDir)) { throw "Phase A feature directory not found: $FeatDir" }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    $code = Invoke-PythonFile $Atlas @("--features-dir",$FeatDir,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase B atlas failed, exit=$code" }

    $pubArgs = @("--phase","phase-b-atlas","--status","PASS","--summary","Phase B coarse phenomenon atlas completed. 2024 discovery and 2025 internal confirmation finished; 2026 untouched.")
    foreach ($p in @($Summary,$Shortlist,$Survivors)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-PythonFile $Publisher $pubArgs
    if ($pubCode -ne 0) { Write-Warning "Atlas PASS but automatic GitHub publication failed." }

    Write-Host ""
    Write-Host "=== PHASE B ATLAS READY AND PUBLICATION ATTEMPTED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $pubCode = Invoke-PythonFile $Publisher @("--phase","phase-b-atlas","--status","FAIL","--summary",$message)
        if ($pubCode -ne 0) { Write-Warning "Failure publication also failed." }
    } catch {}
    exit 1
}
