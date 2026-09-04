param(
    [Parameter(Mandatory=$true)][string]$RunId,
    [Parameter(Mandatory=$true)][string]$RawDir,
    [Parameter(Mandatory=$true)][string]$PublishDir,
    [Parameter(Mandatory=$true)][string]$FromDate,
    [Parameter(Mandatory=$true)][string]$ToDate,
    [Parameter(Mandatory=$true)][string]$HostSymbol,
    [Parameter(Mandatory=$true)][string]$Symbol1,
    [Parameter(Mandatory=$true)][string]$Symbol2,
    [Parameter(Mandatory=$true)][string]$TerminalBuild,
    [Parameter(Mandatory=$true)][string]$TargetAccount,
    [Parameter(Mandatory=$true)][string]$TargetServer,
    [Parameter(Mandatory=$true)][string]$GeneratedHarness,
    [Parameter(Mandatory=$true)][string]$TesterConfig,
    [switch]$NoGitHubPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Analyzer = Join-Path $RepoRoot 'automation\analyze_d025_backtest_v1.py'
$SourceEa = Join-Path $RepoRoot 'research\ea\D025_LER_Observer_V0.mq5'
$RulesLock = Join-Path $RepoRoot 'research\campaigns\D025_LER_V0_RULES_LOCK_2026_09_04.md'
$ResultsClone = 'D:\MT5_Backtests\guardian-backtest-results'
$ResultsBranch = 'backtest-results'

function Get-Sha256([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Find-Python {
    $venv = Join-Path $RepoRoot 'research\external_intelligence\.venv\Scripts\python.exe'
    if (Test-Path $venv) { return $venv }
    $p = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($p) { return $p.Source }
    throw 'Python not found.'
}

function Ensure-ResultsClone {
    $remote = (& git -C $RepoRoot remote get-url origin).Trim()
    if (-not (Test-Path (Join-Path $ResultsClone '.git'))) {
        if (Test-Path $ResultsClone) { Remove-Item -Recurse -Force $ResultsClone }
        & git clone --quiet $remote $ResultsClone
        if ($LASTEXITCODE -ne 0) { throw 'Could not clone result workspace.' }
    }
    & git -C $ResultsClone fetch --quiet origin $ResultsBranch
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch origin/$ResultsBranch" }
    & git -C $ResultsClone checkout -q -B $ResultsBranch "origin/$ResultsBranch"
    if ($LASTEXITCODE -ne 0) { throw "Could not checkout $ResultsBranch" }
}

if (-not (Test-Path $Analyzer)) { throw "Missing analyzer: $Analyzer" }
if (-not (Test-Path (Join-Path $RawDir 'events.csv'))) { throw 'events.csv missing.' }
New-Item -ItemType Directory -Force -Path $PublishDir | Out-Null

$python = Find-Python
& $python $Analyzer `
    --run-dir $RawDir `
    --output-dir $PublishDir `
    --run-id $RunId `
    --from-date $FromDate `
    --to-date $ToDate `
    --host-symbol $HostSymbol `
    --symbol1 $Symbol1 `
    --symbol2 $Symbol2 `
    --terminal-label 'FundedNext-Server 2 / account 14202634' `
    --model 4
if ($LASTEXITCODE -ne 0) { throw 'D025 analyzer failed.' }

$repoCommit = (& git -C $RepoRoot rev-parse HEAD).Trim()
$manifest = [ordered]@{
    schema = 2
    run_id = $RunId
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    source_commit = $repoCommit
    d025_source = 'research/ea/D025_LER_Observer_V0.mq5'
    d025_source_sha256 = Get-Sha256 $SourceEa
    locked_rules = 'research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md'
    locked_rules_sha256 = Get-Sha256 $RulesLock
    generated_harness_sha256 = Get-Sha256 $GeneratedHarness
    tester_config_sha256 = Get-Sha256 $TesterConfig
    target = [ordered]@{
        broker = 'FundedNext Ltd'
        account = $TargetAccount
        server = $TargetServer
        account_mode = 'Hedge'
        terminal_build = $TerminalBuild
        isolated_portable_clone = $true
    }
    tester = [ordered]@{
        from_date = $FromDate
        to_date = $ToDate
        host_symbol = $HostSymbol
        symbol1 = $Symbol1
        symbol2 = $Symbol2
        period = 'M1'
        model = 4
        model_label = 'Every tick based on real ticks'
        optimization = $false
        live_trading_allowed = $false
    }
    raw = [ordered]@{}
}
foreach ($name in @('events.csv','virtual_trades.csv','outcomes.csv','COMPLETE.txt')) {
    $p = Join-Path $RawDir $name
    if (Test-Path $p) {
        $manifest.raw[$name] = [ordered]@{ size_bytes=(Get-Item $p).Length; sha256=Get-Sha256 $p }
    }
}
$manifest | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $PublishDir 'manifest.json') -Encoding UTF8

if ($NoGitHubPush) {
    Write-Host 'GitHub push skipped.'
    exit 0
}

Ensure-ResultsClone
$dest = Join-Path $ResultsClone "backtests\d025\$RunId"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($name in @('SUMMARY.md','summary.json','manifest.json')) {
    Copy-Item (Join-Path $PublishDir $name) (Join-Path $dest $name) -Force
}
$compact = Join-Path $PublishDir 'events_compact.csv'
if ((Test-Path $compact) -and (Get-Item $compact).Length -le 5MB) {
    Copy-Item $compact (Join-Path $dest 'events_compact.csv') -Force
}
& git -C $ResultsClone add -- "backtests/d025/$RunId"
& git -C $ResultsClone -c user.name='Guardian Backtest Bot' -c user.email='guardian-backtest@local' commit -m "D025 FundedNext Server2 backtest $RunId"
if ($LASTEXITCODE -ne 0) { throw 'git commit failed.' }
& git -C $ResultsClone push origin $ResultsBranch
if ($LASTEXITCODE -ne 0) { throw 'git push failed.' }
Write-Host "Published: branch $ResultsBranch / backtests/d025/$RunId"