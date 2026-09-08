$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Summary = Join-Path $OutDir "phase_b_summary.json"
$Shortlist = Join-Path $OutDir "phase_b_shortlist_and_confirmation.csv"
$Survivors = Join-Path $OutDir "phase_b_survivors.csv"

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
    $lines = & $exe @prefix $Script @Arguments 2>&1
    $code = $LASTEXITCODE
    foreach ($line in @($lines)) { Write-Host $line }
    return [int]$code
}

foreach ($required in @($Summary,$Shortlist,$Survivors)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required Phase B artifact missing: $required"
    }
}

Write-Host "Publishing existing Phase B artifacts to GitHub..." -ForegroundColor Cyan
$pubCode = Invoke-PythonFile $Publisher @(
    "--phase","phase-b-atlas",
    "--status","PASS",
    "--summary","Recovered publication of completed Phase B atlas. Computation completed locally; 2024 discovery and 2025 internal confirmation; 2026 untouched.",
    "--artifact",$Summary,
    "--artifact",$Shortlist,
    "--artifact",$Survivors
)
if ($pubCode -ne 0) { throw "Phase B publication failed, exit=$pubCode" }
Write-Host "PHASE B PUBLICATION OK" -ForegroundColor Green
