param(
    [string]$FromDate = '2025.01.01',
    [string]$ToDate = '2026.06.28',
    [string]$HostSymbol = 'BTCUSD',
    [string]$Symbol1 = 'BTCUSD',
    [string]$Symbol2 = 'ETHUSD',
    [string]$TerminalDataPath = '',
    [int]$TimeoutMinutes = 480,
    [switch]$NoGitHubPush
)

Write-Warning 'D025 FundedNext backtest V1 is superseded. Redirecting to V2 exact target: account 14202634 / FundedNext-Server 2.'
$v2 = Join-Path $PSScriptRoot 'run_d025_fundednext_backtest_v2.ps1'
if (-not (Test-Path $v2)) { throw "Missing V2 runner: $v2" }

& $v2 `
    -FromDate $FromDate `
    -ToDate $ToDate `
    -HostSymbol $HostSymbol `
    -Symbol1 $Symbol1 `
    -Symbol2 $Symbol2 `
    -TerminalDataPath $TerminalDataPath `
    -TimeoutMinutes $TimeoutMinutes `
    -NoGitHubPush:$NoGitHubPush
exit $LASTEXITCODE
