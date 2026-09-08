$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ia_v1"
$Checker = Join-Path $PSScriptRoot "check_propfirm_news_mask_v1_01.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"
$Policy = Join-Path $PSScriptRoot "phase_ia_news_policy_v1.json"

$Summary = Join-Path $OutDir "phase_ia_summary.json"
$Integrity = Join-Path $OutDir "phase_ia_integrity.json"
$Events = Join-Path $OutDir "phase_ia_xauusd_high_impact_events_2024_2025.csv"
$Mask = Join-Path $OutDir "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
$Manifest = Join-Path $OutDir "mt5_calendar_terminal_manifest.txt"
$Raw = Join-Path $OutDir "mt5_high_impact_calendar_2024_2025.csv"

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
    if ($cmd.Count -gt 1) { $prefix = $cmd[1..($cmd.Count-1)] }
    & $exe @prefix @Arguments | Out-Host
    return [int]$LASTEXITCODE
}

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE I-A RECOVERY v1.03 ===" -ForegroundColor Cyan
Write-Host "Reuses the already exported FundedNext MT5 calendar and mask."
Write-Host "Fix only: MT5 month key YYYY.MM is normalized to YYYY-MM for coverage checking."
Write-Host "No MT5 script rerun. No new calendar download. 2026 remains untouched."
Write-Host ""

try {
    foreach ($p in @($Summary,$Events,$Mask,$Manifest,$Raw,$Checker,$Publisher,$Policy)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Required recovery artifact missing: $p" }
    }

    $code = Invoke-Python @("-m","py_compile",$Checker,$Publisher)
    if ($code -ne 0) { throw "Phase I-A recovery Python preflight failed, exit=$code" }

    $code = Invoke-Python @($Checker,"--input-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-A corrected integrity gate still failed, exit=$code" }

    $pubArgs = @(
        $Publisher,
        "--phase","phase-ia-news-mask",
        "--status","PASS",
        "--summary","Phase I-A PASS after checker-only recovery. Original FundedNext-Server 2 MT5 export reused unchanged; false FAIL was caused solely by MT5 YYYY.MM versus checker YYYY-MM month-key formatting. Conservative XAUUSD USD high-impact +/-5m mask integrity passes; 2026 untouched."
    )
    foreach ($p in @($Summary,$Integrity,$Events,$Mask,$Manifest,$Raw,$Policy)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase I-A corrected gate passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE I-A RECOVERED AND PUBLISHED PASS ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try { $null = Invoke-Python @($Publisher,"--phase","phase-ia-news-mask","--status","FAIL","--summary",$message) } catch {}
    exit 1
}
