$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$source = Join-Path $repoRoot 'research\ea\Guardian_SharedIntel_ReadOnlyProbe_v1.mq5'
if (-not (Test-Path $source)) {
    throw "Probe source not found: $source"
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
        $dest = Join-Path $destDir 'Guardian_SharedIntel_ReadOnlyProbe_v1.mq5'
        Copy-Item -Path $source -Destination $dest -Force
        $targets += $dest
    }
}

Write-Host ''
Write-Host '=== Guardian MT5 read-only probe deployment ==='
Write-Host ("Source: {0}" -f $source)
Write-Host ("Standard MT5 data folders updated: {0}" -f $targets.Count)
foreach ($t in $targets) {
    Write-Host ("  -> {0}" -f $t)
}
Write-Host ''
if ($targets.Count -lt 2) {
    Write-Warning 'Fewer than 2 standard MT5 data folders were found. Portable-mode terminals may require manual copy into their own MQL5\Experts\GuardianResearch folder.'
}
Write-Host 'Next: in each MT5 terminal, press F4, open Experts\GuardianResearch\Guardian_SharedIntel_ReadOnlyProbe_v1.mq5 and press F7 to compile.'
