$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1"

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

$Builder = Join-Path $PSScriptRoot "build_binance_orderflow_context_v1_00.py"
$Checker = Join-Path $PSScriptRoot "check_binance_orderflow_context_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Manifest = Join-Path $OutDir "binance_orderflow_manifest_v1.json"
$Integrity = Join-Path $OutDir "binance_orderflow_integrity_v1.json"

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE F-A ===" -ForegroundColor Cyan
Write-Host "Binance spot + USD-M 5m aggressive-flow context."
Write-Host "BTC/ETH, 2024-2025 only. Dataset/integrity only. No rule search."
Write-Host ""

try {
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    Write-Host "Preflight: Python syntax check..."
    $code = Invoke-Python @("-m","py_compile",$Builder,$Checker,$Publisher)
    if ($code -ne 0) { throw "Phase F-A Python preflight failed, exit=$code" }

    $code = Invoke-Python @($Builder,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase F-A orderflow build failed, exit=$code" }

    $code = Invoke-Python @($Checker,"--input-dir",$OutDir)
    if ($code -ne 0) { throw "Phase F-A integrity gate failed, exit=$code" }

    $pubArgs = @(
        $Publisher,
        "--phase","phase-fa-binance-orderflow",
        "--status","PASS",
        "--summary","Phase F-A Binance spot+USD-M 5m aggressive-flow dataset passed integrity. BTC/ETH 2024-2025 only; checksum-verified archives; 2026 untouched; no rule search executed."
    )
    foreach ($p in @($Manifest,$Integrity)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase F-A passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE F-A COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try {
        $null = Invoke-Python @(
            $Publisher,
            "--phase","phase-fa-binance-orderflow",
            "--status","FAIL",
            "--summary",$message
        )
    } catch {}
    exit 1
}
