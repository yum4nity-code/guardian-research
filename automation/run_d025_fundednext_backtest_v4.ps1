param(
    [string]$FromDate = '2025.01.01',
    [string]$ToDate = '2026.06.28',
    [string]$HostSymbol = 'BTCUSD',
    [string]$Symbol1 = 'BTCUSD',
    [string]$Symbol2 = 'ETHUSD',
    [string]$TargetAccount = '14202634',
    [string]$TargetServer = 'FundedNext-Server 2',
    [int]$TimeoutMinutes = 480,
    [switch]$NoGitHubPush
)

$ErrorActionPreference = 'Stop'
$V3 = Join-Path $PSScriptRoot 'run_d025_fundednext_backtest_v3.ps1'
if (-not (Test-Path $V3)) { throw "Missing V3 runner: $V3" }

Write-Host ''
Write-Host '=== D025 FundedNext V4: stable launcher ===' -ForegroundColor Cyan
Write-Host 'Exact live window verifies account + server; portable clone verifies exact account.' -ForegroundColor DarkGray

$args = @(
    '-NoProfile','-ExecutionPolicy','Bypass','-File',$V3,
    '-FromDate',$FromDate,
    '-ToDate',$ToDate,
    '-HostSymbol',$HostSymbol,
    '-Symbol1',$Symbol1,
    '-Symbol2',$Symbol2,
    '-TargetAccount',$TargetAccount,
    '-TargetServer',$TargetServer,
    '-TimeoutMinutes',$TimeoutMinutes
)
if ($NoGitHubPush) { $args += '-NoGitHubPush' }

& powershell.exe @args
$rc = $LASTEXITCODE
if ($rc -ne 0) { throw "V4 delegated run failed with exit code $rc." }
