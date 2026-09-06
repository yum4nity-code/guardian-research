param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$CommonFiles = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$ResultsRepo = 'D:\MT5_Backtests\guardian-backtest-autosync-results'
$Branch = 'backtest-results'
$WatcherRuntime = 'D:\MT5_Backtests\automation\Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE.ps1'
$Symbols = @('BTCUSD','ETHUSD','EURUSD','GBPUSD','USDJPY','XAUUSD')
$Stage = 'DEV_2024_2025'
$StatsPattern = 'D037_V100_DEV_2024_2025_{0}_STATS.csv'
$TradesPattern = 'D037_V100_DEV_2024_2025_{0}_TRADES.csv'

function Invoke-Git([string[]]$Args) {
    $out = & git @Args 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git $($Args -join ' ') failed:`n$($out -join "`n")" }
    return @($out)
}

function Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Sanitize-Stats([string]$Source,[string]$Destination) {
    $raw = Get-Content -LiteralPath $Source -Raw
    if ($env:USERPROFILE) { $raw = $raw.Replace($env:USERPROFILE,'C:\Users\<REDACTED>') }
    if ($env:USERNAME) { $raw = $raw.Replace("C:\Users\$($env:USERNAME)",'C:\Users\<REDACTED>') }
    Set-Content -LiteralPath $Destination -Value $raw -Encoding UTF8
}

function Get-ValidatedPair([string]$Symbol) {
    $statsName = $StatsPattern -f $Symbol
    $tradesName = $TradesPattern -f $Symbol
    $statsPath = Join-Path $CommonFiles $statsName
    $tradesPath = Join-Path $CommonFiles $tradesName
    if (-not (Test-Path -LiteralPath $statsPath)) { throw "$Symbol: STATS missing: $statsPath" }
    if (-not (Test-Path -LiteralPath $tradesPath)) { throw "$Symbol: TRADES missing: $tradesPath" }

    $rows = @(Import-Csv -LiteralPath $statsPath -Delimiter ';')
    $finals = @($rows | Where-Object { $_.status -eq 'FINAL' })
    if ($finals.Count -lt 1) { throw "$Symbol: no FINAL row" }
    $f = $finals[-1]

    if ($f.run_stage -ne $Stage) { throw "$Symbol: stage mismatch: $($f.run_stage)" }
    if ($f.timeframe -ne 'PERIOD_M15') { throw "$Symbol: timeframe mismatch: $($f.timeframe)" }
    if ($f.symbol -notmatch [regex]::Escape($Symbol)) { throw "$Symbol: symbol mismatch: $($f.symbol)" }

    $opened=[int64]$f.trades_opened; $closed=[int64]$f.trades_closed; $csvRows=[int64]$f.csv_trade_rows
    if ($opened -le 0 -or $opened -ne $closed -or $closed -ne $csvRows) {
        throw "$Symbol: integrity mismatch opened=$opened closed=$closed rows=$csvRows"
    }
    foreach($field in @('invalid_price','invalid_risk','risk_calc_failures','pnl_calc_failures')) {
        if ([int64]$f.$field -ne 0) { throw "$Symbol: $field=$($f.$field)" }
    }

    $tradeRows = @(Import-Csv -LiteralPath $tradesPath -Delimiter ';')
    if ($tradeRows.Count -ne $csvRows) { throw "$Symbol: physical trade rows=$($tradeRows.Count), FINAL says $csvRows" }
    if (@($tradeRows | Where-Object { $_.run_stage -ne $Stage }).Count -gt 0) { throw "$Symbol: trade stage mismatch" }

    [pscustomobject]@{Symbol=$Symbol;StatsName=$statsName;TradesName=$tradesName;StatsPath=$statsPath;TradesPath=$tradesPath;Rows=$csvRows}
}

if (-not (Test-Path -LiteralPath $CommonFiles)) { throw "MT5 FILE_COMMON missing: $CommonFiles" }
if (-not (Test-Path -LiteralPath (Join-Path $ResultsRepo '.git'))) { throw "Results git clone missing: $ResultsRepo" }

Write-Host '=== D037 FORCE FLUSH ==='
Write-Host 'Validating local result pairs...'
$pairs = @()
foreach($s in $Symbols) {
    $p = Get-ValidatedPair $s
    $pairs += $p
    Write-Host ("OK {0}: {1} rows" -f $s,$p.Rows)
}

# Pause only the Guardian result watcher so it cannot race this one-shot git transaction.
$stoppedWatcher=$false
$watchers=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE\.ps1' })
foreach($p in $watchers) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    $stoppedWatcher=$true
    Write-Host "Paused AutoSync watcher PID $($p.ProcessId)"
}

try {
    Push-Location $ResultsRepo
    try {
        $dirty = @(& git status --porcelain 2>$null)
        if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
        if ($dirty.Count -gt 0) { throw "Results clone is dirty; refusing destructive operation:`n$($dirty -join "`n")" }

        Invoke-Git @('fetch','origin',$Branch) | Out-Null
        Invoke-Git @('checkout',$Branch) | Out-Null
        Invoke-Git @('pull','--ff-only','origin',$Branch) | Out-Null

        $recent = (Invoke-Git @('log','-250','--pretty=format:%s')) -join "`n"
        $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        $datePath = Get-Date -Format 'yyyy/MM/dd'
        $published = New-Object System.Collections.Generic.List[string]

        foreach($p in $pairs) {
            if ($recent -match [regex]::Escape("_D037_$($p.Symbol)_")) {
                Write-Host "SKIP $($p.Symbol): already published on branch"
                continue
            }

            $tmpStats = Join-Path $env:TEMP ("D037_FLUSH_{0}_{1}" -f $p.Symbol,$p.StatsName)
            Sanitize-Stats $p.StatsPath $tmpStats
            $finger = ((Sha256 $tmpStats) + (Sha256 $p.TradesPath))
            $fingerBytes=[Text.Encoding]::UTF8.GetBytes($finger)
            $sha=[Security.Cryptography.SHA256]::Create()
            try { $finger12=([BitConverter]::ToString($sha.ComputeHash($fingerBytes))).Replace('-','').ToLowerInvariant().Substring(0,12) }
            finally { $sha.Dispose() }

            $runId = "${stamp}_D037_$($p.Symbol)_manualflush_$finger12"
            $destRel = "backtests/inbox/$datePath/$runId"
            $dest = Join-Path $ResultsRepo ($destRel -replace '/','\')
            New-Item -ItemType Directory -Force -Path $dest | Out-Null

            Copy-Item -LiteralPath $tmpStats -Destination (Join-Path $dest $p.StatsName) -Force
            Copy-Item -LiteralPath $p.TradesPath -Destination (Join-Path $dest $p.TradesName) -Force
            Remove-Item -LiteralPath $tmpStats -Force -ErrorAction SilentlyContinue

            $manifest=[ordered]@{
                schema=1
                reason='MANUAL_D037_FORCE_FLUSH_VALIDATED'
                run_id=$runId
                strategy='D037'
                stage=$Stage
                symbol=$p.Symbol
                csv_trade_rows=$p.Rows
                files=@(
                    [ordered]@{name=$p.StatsName;sha256=(Sha256 (Join-Path $dest $p.StatsName));sanitized=$true},
                    [ordered]@{name=$p.TradesName;sha256=(Sha256 (Join-Path $dest $p.TradesName));sanitized=$false}
                )
            }
            $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $dest 'sync_manifest.json') -Encoding UTF8
            Invoke-Git @('add','--',$destRel) | Out-Null
            $published.Add($p.Symbol)
            Write-Host "STAGED $($p.Symbol) -> $destRel"
        }

        if ($published.Count -eq 0) {
            Write-Host 'Nothing to publish: all six D037 symbols are already on GitHub.'
        } else {
            $msg='Manual flush validated D037 DEV CSVs '+($published -join ',')
            Invoke-Git @('commit','-m',$msg) | Out-Null
            $push=& git push origin $Branch 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host 'First push raced another writer; rebasing once...'
                Invoke-Git @('pull','--rebase','origin',$Branch) | Out-Null
                Invoke-Git @('push','origin',$Branch) | Out-Null
            }
            $head=(Invoke-Git @('rev-parse','HEAD'))[0]
            Write-Host ("PUBLISHED: {0}" -f ($published -join ', '))
            Write-Host "COMMIT: $head"
        }
    }
    finally { Pop-Location }
}
finally {
    if ((Test-Path -LiteralPath $WatcherRuntime) -and ($stoppedWatcher -or $watchers.Count -eq 0)) {
        Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$WatcherRuntime`"")
        Start-Sleep -Seconds 2
        Write-Host 'AutoSync watcher restarted.'
    }
}

Write-Host 'DONE'
