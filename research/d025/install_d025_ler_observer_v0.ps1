$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$source = Join-Path $repoRoot 'research\ea\D025_LER_Observer_V0.mq5'
if (-not (Test-Path $source)) {
    throw "D025 source not found: $source"
}

$terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
if (-not (Test-Path $terminalRoot)) {
    throw "MetaTrader terminal data root not found: $terminalRoot"
}

$targets = @()
Get-ChildItem -Path $terminalRoot -Directory | ForEach-Object {
    if ($_.Name -eq 'Common') { return }
    $mql5 = Join-Path $_.FullName 'MQL5'
    if (Test-Path $mql5) {
        $destDir = Join-Path $mql5 'Experts\GuardianResearch'
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        $dest = Join-Path $destDir 'D025_LER_Observer_V0.mq5'
        Copy-Item -Path $source -Destination $dest -Force
        $targets += $dest
    }
}

Write-Host ''
Write-Host '============================================================'
Write-Host ' D025 LER OBSERVER V0 - MT5 DEPLOYMENT'
Write-Host ' RESEARCH ONLY / VIRTUAL TRADES / NO LIVE ORDERS'
Write-Host '============================================================'
Write-Host ("Source: {0}" -f $source)
Write-Host ("MT5 data folders updated: {0}" -f $targets.Count)
foreach ($t in $targets) {
    Write-Host ("  -> {0}" -f $t)
}
Write-Host ''
if ($targets.Count -eq 0) {
    throw 'No standard MT5 MQL5 folder found.'
}
if ($targets.Count -lt 2) {
    Write-Warning 'Only one standard MT5 data folder was found. Portable terminals may require manual copy.'
}
Write-Host 'NEXT:'
Write-Host '  1. In the FTMO MT5 terminal press F4.'
Write-Host '  2. In MetaEditor open Experts > GuardianResearch > D025_LER_Observer_V0.mq5.'
Write-Host '  3. Press F7 to compile.'
Write-Host '  4. Send the compile result (errors/warnings) before attaching it to a chart.'
