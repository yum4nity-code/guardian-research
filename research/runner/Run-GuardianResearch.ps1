param(
    [string]$Experiment = "D037",
    [switch]$BootstrapOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -3 @Args
    } else {
        $python = Get-Command python -ErrorAction Stop
        & $python.Source @Args
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE: $($Args -join ' ')"
    }
}

$config = Join-Path $RepoRoot "local\guardian_runner.json"
if (-not (Test-Path $config)) {
    Write-Host "[Guardian] Local runner config absent. Autodetecting MT5..."
    Invoke-Python "research/runner/bootstrap_windows.py"
}

Write-Host "[Guardian] Checking project + local environment..."
Invoke-Python "research/runner/guardian_research.py" "doctor" $Experiment

if ($BootstrapOnly) {
    Write-Host "[Guardian] Bootstrap/doctor complete. No compile or backtest launched."
    exit 0
}

Write-Host "[Guardian] Starting deterministic pipeline: compile -> DEV batch -> score"
Invoke-Python "research/runner/guardian_research.py" "run" $Experiment
Write-Host "[Guardian] Pipeline finished. See workspace receipts for evidence/verdict."
