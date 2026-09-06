param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Once,
    [int]$PollSeconds = 5,
    [int]$StableSeconds = 20,
    [int]$GitAttempts = 5
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$TaskLabel      = 'Guardian D023 CSV AutoSync v1.03 GITARGSFIX PUBLICSAFE'
$InstallDir     = 'D:\MT5_Backtests\automation'
$InstalledFile  = Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v1_03_D023_GITARGSFIX_PUBLICSAFE.ps1'
$StartupDir     = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd     = Join-Path $StartupDir 'Guardian_D023_CSV_AutoSync_v1_03.cmd'
$OldStartupCmd  = Join-Path $StartupDir 'Guardian_D023_CSV_AutoSync_v1_02.cmd'
$PidFile        = 'D:\MT5_Backtests\guardian-d023-csv-sync-v103.pid'
$OldPidFile     = 'D:\MT5_Backtests\guardian-d023-csv-sync-v102.pid'
$StateFile      = 'D:\MT5_Backtests\guardian-d023-csv-sync-v103-state.json'
$HealthFile     = 'D:\MT5_Backtests\guardian-d023-csv-sync-v103-health.json'
$LogFile        = 'D:\MT5_Backtests\logs\guardian-d023-csv-sync-v103.log'
$ResultsClone   = 'D:\MT5_Backtests\guardian-backtest-autosync-results'
$ResultsBranch  = 'backtest-results'
$RepoRoot       = 'D:\MT5_Backtests\guardian-research'
$RemoteFallback = 'https://github.com/yum4nity-code/guardian-research.git'
$CommonFiles    = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$StatsName      = 'D023_V108_USDJPY_2023_STATS.csv'
$TradesName     = 'D023_V108_USDJPY_2023_TRADES.csv'
$ExpectedSource = 'D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5'
$ExpectedVer    = '1.08'

function Ensure-Parent([string]$Path) {
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
}

function Write-Log([string]$Message) {
    Ensure-Parent $LogFile
    $line = ('{0} | {1}' -f ([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')), $Message)
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    if (-not $Install) { Write-Host $line }
}

function Write-Health([string]$Status,[string]$Message,[string]$Fingerprint='') {
    Ensure-Parent $HealthFile
    $obj = [ordered]@{
        schema = 1
        watcher = $TaskLabel
        updated_at_utc = [DateTime]::UtcNow.ToString('o')
        status = $Status
        message = $Message
        fingerprint = $Fingerprint
        common_files = $CommonFiles
        stats_name = $StatsName
        trades_name = $TradesName
        results_branch = $ResultsBranch
    }
    $tmp = "$HealthFile.tmp"
    $obj | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $HealthFile -Force
}

# IMPORTANT: never name this parameter Args. $args is an automatic PowerShell variable.
function Invoke-GitOnce([string[]]$GitArgs,[switch]$AllowFailure) {
    if (-not $GitArgs -or $GitArgs.Count -eq 0) { throw 'internal error: empty GitArgs' }
    $output = & git @GitArgs 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "git $($GitArgs -join ' ') failed ($code): $($output -join ' ')"
    }
    return [pscustomobject]@{ Code=$code; Output=@($output) }
}

function Invoke-GitRetry([string[]]$GitArgs) {
    if (-not $GitArgs -or $GitArgs.Count -eq 0) { throw 'internal error: empty GitArgs retry' }
    $attempts = [Math]::Max(1,$GitAttempts)
    for ($i=1; $i -le $attempts; $i++) {
        $r = Invoke-GitOnce -GitArgs $GitArgs -AllowFailure
        if ($r.Code -eq 0) { return $r }
        if ($i -ge $attempts) {
            throw "git $($GitArgs -join ' ') failed after $attempts attempts: $($r.Output -join ' ')"
        }
        $delay = [Math]::Min(60,[Math]::Pow(2,$i))
        Write-Log "WARN git retry $i/$attempts in ${delay}s | $($GitArgs -join ' ')"
        Start-Sleep -Seconds ([int]$delay)
    }
}

function Get-RemoteUrl {
    if (Test-Path -LiteralPath (Join-Path $RepoRoot '.git')) {
        try {
            $r = Invoke-GitOnce -GitArgs @('-C',$RepoRoot,'remote','get-url','origin')
            $u = (($r.Output | Select-Object -First 1).ToString()).Trim()
            if ($u) { return $u }
        } catch {}
    }
    return $RemoteFallback
}

function Ensure-ResultsClone {
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
        throw 'git.exe introuvable. Git doit etre installe et authentifie sur GitHub.'
    }

    if (-not (Test-Path -LiteralPath (Join-Path $ResultsClone '.git'))) {
        if (Test-Path -LiteralPath $ResultsClone) {
            $backup = "$ResultsClone.bad.$([DateTime]::Now.ToString('yyyyMMdd_HHmmss'))"
            Move-Item -LiteralPath $ResultsClone -Destination $backup
            Write-Log "Moved incomplete results clone to $backup"
        }
        Ensure-Parent (Join-Path $ResultsClone 'dummy')
        $remote = Get-RemoteUrl
        Write-Log "Clone $ResultsBranch depuis $remote"
        Invoke-GitRetry -GitArgs @('clone','--quiet','--branch',$ResultsBranch,'--single-branch',$remote,$ResultsClone) | Out-Null
    }

    $branch = Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'rev-parse','--abbrev-ref','HEAD')
    if ((($branch.Output | Select-Object -First 1).ToString()).Trim() -ne $ResultsBranch) {
        Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'checkout','-q',$ResultsBranch) | Out-Null
    }
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch) | Out-Null
}

function Get-Hash([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-StateFingerprint {
    if (-not (Test-Path -LiteralPath $StateFile)) { return '' }
    try {
        $obj = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
        if ($obj.last_published_fingerprint) { return $obj.last_published_fingerprint.ToString() }
    } catch {}
    return ''
}

function Save-State([string]$Fingerprint,[string]$RunId) {
    Ensure-Parent $StateFile
    [ordered]@{
        schema = 1
        updated_at_utc = [DateTime]::UtcNow.ToString('o')
        last_published_fingerprint = $Fingerprint
        last_run_id = $RunId
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$StateFile.tmp" -Encoding UTF8
    Move-Item -LiteralPath "$StateFile.tmp" -Destination $StateFile -Force
}

function Get-StableSignature([string]$Path) {
    $f = Get-Item -LiteralPath $Path
    return ('{0}|{1}' -f $f.Length,$f.LastWriteTimeUtc.Ticks)
}

function Import-D023([string]$StatsPath,[string]$TradesPath) {
    $stats = @(Import-Csv -LiteralPath $StatsPath -Delimiter ';')
    if ($stats.Count -lt 3) { throw 'D023 STATS incomplete: expected INIT/READY/FINAL rows.' }
    $statuses = @($stats | ForEach-Object { $_.status })
    $initIndex = [Array]::IndexOf($statuses,'INIT')
    $readyIndex = [Array]::IndexOf($statuses,'READY')
    $finalIndex = [Array]::LastIndexOf($statuses,'FINAL')
    if ($initIndex -lt 0 -or $readyIndex -lt 0 -or $finalIndex -lt 0 -or -not ($initIndex -lt $readyIndex -and $readyIndex -lt $finalIndex)) {
        throw 'D023 STATS status sequence invalid; require INIT -> READY -> FINAL.'
    }
    $final = $stats[$finalIndex]
    if ($final.source_name -ne $ExpectedSource) { throw "unexpected D023 source_name: $($final.source_name)" }
    if ($final.source_version -ne $ExpectedVer) { throw "unexpected D023 source_version: $($final.source_version)" }
    if ($final.symbol -notmatch 'USDJPY') { throw "unexpected D023 symbol: $($final.symbol)" }
    if ($final.timeframe -ne 'PERIOD_M15') { throw "unexpected D023 timeframe: $($final.timeframe)" }
    $closed = 0
    $csvRows = 0
    if (-not [int]::TryParse($final.trades_closed,[ref]$closed)) { throw 'invalid trades_closed in D023 FINAL.' }
    if (-not [int]::TryParse($final.csv_trade_rows,[ref]$csvRows)) { throw 'invalid csv_trade_rows in D023 FINAL.' }
    if ($closed -ne $csvRows) { throw "D023 counter mismatch: trades_closed=$closed csv_trade_rows=$csvRows" }
    $trades = @(Import-Csv -LiteralPath $TradesPath -Delimiter ';')
    if ($trades.Count -ne $closed) { throw "D023 TRADES row mismatch: rows=$($trades.Count) trades_closed=$closed" }
    return [pscustomobject]@{ Stats=$stats; Final=$final; Trades=$trades; TradesClosed=$closed }
}

function Copy-PublicSafeSnapshot([string]$Source,[string]$Destination,[switch]$RedactWindowsUserPath) {
    Ensure-Parent $Destination
    $raw = Get-Content -LiteralPath $Source -Raw -ErrorAction Stop
    if ($RedactWindowsUserPath) {
        $raw = [regex]::Replace($raw,'(?i)([A-Z]:\\Users\\)[^\\;,"\r\n]+','$1<REDACTED>')
    }
    foreach ($rx in @('(?i)password','(?i)api[_-]?key','(?i)secret','(?i)credential','(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}')) {
        if ($raw -match $rx) { throw "PUBLICSAFE block on $([IO.Path]::GetFileName($Source)): sensitive pattern detected" }
    }
    if ($raw -match '(?i)[A-Z]:\\Users\\(?!<REDACTED>)[^\\;,"\r\n]+') {
        throw "PUBLICSAFE block on $([IO.Path]::GetFileName($Source)): unredacted Windows user path remains"
    }
    Set-Content -LiteralPath $Destination -Value $raw -Encoding UTF8
}

function Publish-D023([string]$StatsPath,[string]$TradesPath) {
    $statsHashBefore = Get-Hash $StatsPath
    $tradesHashBefore = Get-Hash $TradesPath
    $validated = Import-D023 -StatsPath $StatsPath -TradesPath $TradesPath
    $statsHashAfter = Get-Hash $StatsPath
    $tradesHashAfter = Get-Hash $TradesPath
    if ($statsHashBefore -ne $statsHashAfter -or $tradesHashBefore -ne $tradesHashAfter) {
        throw 'D023 outputs changed during validation; retry after they stabilize.'
    }

    $statsInfo = Get-Item -LiteralPath $StatsPath
    $tradesInfo = Get-Item -LiteralPath $TradesPath
    $fingerSeed = "$StatsName|$($statsInfo.LastWriteTimeUtc.Ticks)|$statsHashAfter|$TradesName|$($tradesInfo.LastWriteTimeUtc.Ticks)|$tradesHashAfter"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($fingerSeed)
        $fingerprint = (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '')
    } finally { $sha.Dispose() }

    if ((Get-StateFingerprint) -eq $fingerprint) {
        Write-Health -Status 'OK' -Message 'Current finalized D023 pair already published.' -Fingerprint $fingerprint
        return $false
    }

    Ensure-ResultsClone
    $stamp = $statsInfo.LastWriteTimeUtc.ToString('yyyyMMdd_HHmmss')
    $runId = '{0}_D023_V108_USDJPY_{1}' -f $stamp,$fingerprint.Substring(0,12)
    $rel = 'backtests/inbox/{0}/{1}/{2}/{3}' -f $statsInfo.LastWriteTimeUtc.ToString('yyyy'),$statsInfo.LastWriteTimeUtc.ToString('MM'),$statsInfo.LastWriteTimeUtc.ToString('dd'),$runId
    $dest = Join-Path $ResultsClone ($rel -replace '/','\')
    $manifestPath = Join-Path $dest 'sync_manifest.json'

    if (Test-Path -LiteralPath $manifestPath) {
        try {
            $old = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            if ($old.fingerprint -eq $fingerprint) {
                Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null
                Save-State -Fingerprint $fingerprint -RunId $runId
                Write-Health -Status 'OK' -Message 'D023 publication already present and pushed.' -Fingerprint $fingerprint
                return $false
            }
        } catch {}
        throw "deterministic run path collision: $rel"
    }

    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $statsDest = Join-Path $dest $StatsName
    $tradesDest = Join-Path $dest $TradesName
    Copy-PublicSafeSnapshot -Source $StatsPath -Destination $statsDest -RedactWindowsUserPath
    Copy-PublicSafeSnapshot -Source $TradesPath -Destination $tradesDest
    $published = Import-D023 -StatsPath $statsDest -TradesPath $tradesDest

    $manifest = [ordered]@{
        schema = 3
        run_id = $runId
        fingerprint = $fingerprint
        synced_at_utc = $statsInfo.LastWriteTimeUtc.ToString('o')
        reason = 'D023_V108_FINAL_VALIDATED'
        branch = $ResultsBranch
        autosync_version = '1.03'
        validation = [ordered]@{
            required_status_sequence = 'INIT -> READY -> FINAL'
            source_name = $ExpectedSource
            source_version = $ExpectedVer
            symbol = $published.Final.symbol
            timeframe = $published.Final.timeframe
            trades_closed = $published.TradesClosed
            csv_trade_rows = [int]$published.Final.csv_trade_rows
            published_trades_rows = $published.Trades.Count
        }
        files = @(
            [ordered]@{ name=$StatsName; source_sha256=$statsHashAfter; published_sha256=(Get-Hash $statsDest); sanitized=$true },
            [ordered]@{ name=$TradesName; source_sha256=$tradesHashAfter; published_sha256=(Get-Hash $tradesDest); sanitized=$false }
        )
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $latest = [ordered]@{
        schema = 3
        synced_at_utc = $statsInfo.LastWriteTimeUtc.ToString('o')
        run_id = $runId
        path = $rel
        fingerprint = $fingerprint
        reason = 'D023_V108_FINAL_VALIDATED'
        files = @($StatsName,$TradesName,'sync_manifest.json')
    }
    $latestPath = Join-Path $ResultsClone 'backtests\inbox\LATEST.json'
    Ensure-Parent $latestPath
    $latest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $latestPath -Encoding UTF8

    Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'add','--',$rel,'backtests/inbox/LATEST.json') | Out-Null
    $commit = Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'-c','user.name=Guardian Backtest Bot','-c','user.email=guardian-backtest@local','commit','-m',"Auto-sync validated D023 CSV $runId") -AllowFailure
    if ($commit.Code -ne 0) {
        $status = Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'status','--porcelain','--','backtests/inbox')
        if ($status.Output.Count -gt 0) { throw "git commit failed: $($commit.Output -join ' ')" }
    }
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch) | Out-Null
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null

    Save-State -Fingerprint $fingerprint -RunId $runId
    Write-Health -Status 'OK' -Message "PUSH OK $rel" -Fingerprint $fingerprint
    Write-Log "PUSH OK | D023 FINAL VALIDATED | $rel | trades=$($validated.TradesClosed)"
    return $true
}

function Stop-OldV102 {
    if (Test-Path -LiteralPath $OldPidFile) {
        try {
            $oldPid = 0
            $pidText = (Get-Content -LiteralPath $OldPidFile -Raw).Trim()
            if ([int]::TryParse($pidText,[ref]$oldPid)) { Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue }
        } catch {}
    }
    Remove-Item -LiteralPath $OldStartupCmd -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $OldPidFile -Force -ErrorAction SilentlyContinue
}

function Install-Agent {
    Stop-OldV102
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Ensure-Parent $LogFile
    Copy-Item -LiteralPath $PSCommandPath -Destination $InstalledFile -Force
    New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null
    $cmd = '@echo off' + "`r`n" + 'start "Guardian D023 CSV Sync v1.03" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $InstalledFile + '"' + "`r`n"
    Set-Content -LiteralPath $StartupCmd -Value $cmd -Encoding ASCII
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$InstalledFile`"")
    Write-Host "INSTALLE: $InstalledFile"
    Write-Host "AUTOSTART: $StartupCmd"
    Write-Host "HEALTH: $HealthFile"
    Write-Host "LOG: $LogFile"
}

function Uninstall-Agent {
    if (Test-Path -LiteralPath $PidFile) {
        try {
            $workerPid = 0
            $pidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
            if ([int]::TryParse($pidText,[ref]$workerPid)) { Stop-Process -Id $workerPid -Force -ErrorAction SilentlyContinue }
        } catch {}
    }
    Remove-Item -LiteralPath $StartupCmd -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host 'Guardian D023 CSV AutoSync v1.03 desactive.'
}

if ($Install) { Install-Agent; exit 0 }
if ($Uninstall) { Uninstall-Agent; exit 0 }

$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true,'Local\GuardianD023CsvAutoSyncV103GitArgsFixPublicSafe',[ref]$createdNew)
if (-not $createdNew) { exit 0 }
Ensure-Parent $PidFile
Set-Content -LiteralPath $PidFile -Value $PID -Encoding ASCII

$statsPath = Join-Path $CommonFiles $StatsName
$tradesPath = Join-Path $CommonFiles $TradesName
$lastSig = ''
$stableSince = [DateTime]::UtcNow

try {
    Write-Log "$TaskLabel START | pid=$PID | common=$CommonFiles | stable=${StableSeconds}s"
    Write-Health -Status 'STARTING' -Message 'Waiting for finalized D023 v1.08 outputs.'
    while ($true) {
        try {
            if (-not (Test-Path -LiteralPath $statsPath) -or -not (Test-Path -LiteralPath $tradesPath)) {
                Write-Health -Status 'WAITING_OUTPUTS' -Message 'D023 STATS/TRADES pair not present yet.'
            } else {
                $sig = (Get-StableSignature $statsPath) + '|' + (Get-StableSignature $tradesPath)
                $now = [DateTime]::UtcNow
                if ($sig -ne $lastSig) {
                    $lastSig = $sig
                    $stableSince = $now
                }
                $stableFor = ($now - $stableSince).TotalSeconds
                if ($Once -or $stableFor -ge $StableSeconds) {
                    $rawTail = Get-Content -LiteralPath $statsPath -Tail 8 -ErrorAction Stop
                    if ($rawTail -match '(^|;)FINAL(;|$)') {
                        [void](Publish-D023 -StatsPath $statsPath -TradesPath $tradesPath)
                    } else {
                        Write-Health -Status 'WAITING_FINAL' -Message 'D023 files exist but STATS FINAL is not present yet.'
                    }
                }
            }
        } catch {
            $msg = $_.Exception.Message
            Write-Log "ERROR cycle | $msg"
            Write-Health -Status 'ERROR_RETRYING' -Message $msg
        }
        if ($Once) { break }
        Start-Sleep -Seconds ([Math]::Max(2,$PollSeconds))
    }
} finally {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    try { $mutex.ReleaseMutex() } catch {}
    $mutex.Dispose()
    Write-Log "$TaskLabel STOP"
}
