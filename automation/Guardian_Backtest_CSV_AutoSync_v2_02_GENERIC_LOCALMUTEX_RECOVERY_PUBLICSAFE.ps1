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

$TaskLabel      = 'Guardian Backtest CSV AutoSync v2.02 GENERIC LOCALMUTEX RECOVERY PUBLICSAFE'
$InstallDir     = 'D:\MT5_Backtests\automation'
$InstalledFile  = Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v2_02_GENERIC_LOCALMUTEX_RECOVERY_PUBLICSAFE.ps1'
$StartupDir     = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd     = Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync_v2_02.cmd'
$PidFile        = 'D:\MT5_Backtests\guardian-backtest-csv-sync-v202.pid'
$StateFile      = 'D:\MT5_Backtests\guardian-backtest-csv-sync-v202-state.json'
$HealthFile     = 'D:\MT5_Backtests\guardian-backtest-csv-sync-v202-health.json'
$LogFile        = 'D:\MT5_Backtests\logs\guardian-backtest-csv-sync-v202.log'
$ResultsClone   = 'D:\MT5_Backtests\guardian-backtest-autosync-results'
$ResultsBranch  = 'backtest-results'
$RepoRoot       = 'D:\MT5_Backtests\guardian-research'
$RemoteFallback = 'https://github.com/yum4nity-code/guardian-research.git'
$CommonFiles    = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'

$OldStartup = @(
    (Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync_v2_01.cmd'),
    (Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync_v2_00.cmd'),
    (Join-Path $StartupDir 'Guardian_D023_CSV_AutoSync_v1_04.cmd')
)
$OldPid = @(
    'D:\MT5_Backtests\guardian-backtest-csv-sync-v201.pid',
    'D:\MT5_Backtests\guardian-backtest-csv-sync-v200.pid',
    'D:\MT5_Backtests\guardian-d023-csv-sync-v104.pid'
)

function Ensure-Parent([string]$Path) {
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
}

function Write-Log([string]$Message) {
    Ensure-Parent $LogFile
    $line = '{0} | {1}' -f ([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    if (-not $Install) { Write-Host $line }
}

function Write-Health([string]$Status,[string]$Message,[string]$File='') {
    Ensure-Parent $HealthFile
    [ordered]@{
        schema=2
        watcher=$TaskLabel
        updated_at_utc=[DateTime]::UtcNow.ToString('o')
        status=$Status
        message=$Message
        last_file=$File
        common_files=$CommonFiles
        results_branch=$ResultsBranch
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$HealthFile.tmp" -Encoding UTF8
    Move-Item -LiteralPath "$HealthFile.tmp" -Destination $HealthFile -Force
}

function Quote-NativeArg([string]$Value) {
    if ($null -eq $Value -or $Value.Length -eq 0) { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + ($Value -replace '(\\*)"','$1$1\"' -replace '(\\+)$','$1$1') + '"'
}

# Keep the exact native-process pattern proven by D023 AutoSync v1.04.
function Invoke-GitOnce([string[]]$GitArgs,[switch]$AllowFailure) {
    if (-not $GitArgs -or $GitArgs.Count -eq 0) { throw 'internal error: empty GitArgs' }
    $git = (Get-Command git.exe -ErrorAction Stop).Source
    $outFile = Join-Path $env:TEMP ("guardian_git_out_{0}_{1}.txt" -f $PID,[Guid]::NewGuid().ToString('N'))
    $errFile = Join-Path $env:TEMP ("guardian_git_err_{0}_{1}.txt" -f $PID,[Guid]::NewGuid().ToString('N'))
    try {
        $argLine = (($GitArgs | ForEach-Object { Quote-NativeArg $_ }) -join ' ')
        $p = Start-Process -FilePath $git -ArgumentList $argLine -NoNewWindow -Wait -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile
        $stdout = if (Test-Path -LiteralPath $outFile) { @(Get-Content -LiteralPath $outFile -ErrorAction SilentlyContinue) } else { @() }
        $stderr = if (Test-Path -LiteralPath $errFile) { @(Get-Content -LiteralPath $errFile -ErrorAction SilentlyContinue) } else { @() }
        $combined = @($stdout) + @($stderr)
        if ($p.ExitCode -ne 0 -and -not $AllowFailure) {
            throw "git $($GitArgs -join ' ') failed ($($p.ExitCode)): $($combined -join ' ')"
        }
        return [pscustomobject]@{ Code=$p.ExitCode; StdOut=@($stdout); StdErr=@($stderr); Output=@($combined) }
    } finally {
        Remove-Item -LiteralPath $outFile,$errFile -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-GitRetry([string[]]$GitArgs) {
    $attempts = [Math]::Max(1,$GitAttempts)
    for ($i=1; $i -le $attempts; $i++) {
        $r = Invoke-GitOnce -GitArgs $GitArgs -AllowFailure
        if ($r.Code -eq 0) { return $r }
        if ($i -ge $attempts) {
            throw "git $($GitArgs -join ' ') failed after $attempts attempts: $($r.Output -join ' ')"
        }
        Start-Sleep -Seconds ([int][Math]::Min(60,[Math]::Pow(2,$i)))
    }
}

function Get-RemoteUrl {
    if (Test-Path -LiteralPath (Join-Path $RepoRoot '.git')) {
        try {
            $r = Invoke-GitOnce -GitArgs @('-C',$RepoRoot,'remote','get-url','origin')
            $u = (($r.StdOut | Select-Object -First 1).ToString()).Trim()
            if ($u) { return $u }
        } catch {}
    }
    return $RemoteFallback
}

function Ensure-ResultsClone {
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { throw 'git.exe introuvable.' }
    if (-not (Test-Path -LiteralPath (Join-Path $ResultsClone '.git'))) {
        if (Test-Path -LiteralPath $ResultsClone) {
            $backup = "$ResultsClone.bad.$([DateTime]::Now.ToString('yyyyMMdd_HHmmss'))"
            Move-Item -LiteralPath $ResultsClone -Destination $backup
            Write-Log "Moved incomplete results clone to $backup"
        }
        $remote = Get-RemoteUrl
        Invoke-GitRetry -GitArgs @('clone','--quiet','--branch',$ResultsBranch,'--single-branch',$remote,$ResultsClone) | Out-Null
    }

    # Recover a transaction that may have been committed locally before a crash.
    $dirty = Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'status','--porcelain')
    if (@($dirty.StdOut).Count -gt 0) {
        Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'add','-A') | Out-Null
        $c = Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'commit','-m','Recover pending generic autosync transaction') -AllowFailure
        if ($c.Code -eq 0) { Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null }
    }
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch) | Out-Null
}

function Get-Hash([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function Get-StableSignature([string]$Path) { $f=Get-Item -LiteralPath $Path; return ('{0}|{1}' -f $f.Length,$f.LastWriteTimeUtc.Ticks) }

function Get-Fingerprint([string]$StatsPath,[string]$TradesPath) {
    $seed = "$(Split-Path -Leaf $StatsPath)|$(Get-Hash $StatsPath)|$(Split-Path -Leaf $TradesPath)|$(Get-Hash $TradesPath)"
    $sha=[System.Security.Cryptography.SHA256]::Create()
    try { return (($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($seed)) | ForEach-Object { $_.ToString('x2') }) -join '') }
    finally { $sha.Dispose() }
}

function Load-State {
    if (Test-Path -LiteralPath $StateFile) {
        try { return (Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json) } catch {}
    }
    return [pscustomobject]@{ schema=2; installed_at_utc=[DateTime]::UtcNow.ToString('o'); published_fingerprints=@() }
}

function Save-State($State) {
    Ensure-Parent $StateFile
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$StateFile.tmp" -Encoding UTF8
    Move-Item -LiteralPath "$StateFile.tmp" -Destination $StateFile -Force
}

function Is-Published($State,[string]$Fingerprint) {
    return (@($State.published_fingerprints) -contains $Fingerprint)
}

function Mark-Published($State,[string]$Fingerprint) {
    $State.published_fingerprints = @((@($State.published_fingerprints) + @($Fingerprint)) | Select-Object -Unique)
    Save-State $State
}

function Validate-Pair([string]$StatsPath,[string]$TradesPath) {
    $stats = @(Import-Csv -LiteralPath $StatsPath -Delimiter ';')
    if ($stats.Count -lt 3) { throw 'STATS incomplete.' }
    $statuses = @($stats | ForEach-Object { $_.status })
    $i=[Array]::IndexOf($statuses,'INIT')
    $r=[Array]::IndexOf($statuses,'READY')
    $f=[Array]::LastIndexOf($statuses,'FINAL')
    if ($i -lt 0 -or $r -lt 0 -or $f -lt 0 -or -not ($i -lt $r -and $r -lt $f)) {
        throw 'STATS sequence invalid; require INIT -> READY -> FINAL.'
    }
    $final = $stats[$f]
    foreach ($field in @('source_name','source_version','symbol','timeframe','trades_closed','csv_trade_rows')) {
        if (-not ($final.PSObject.Properties.Name -contains $field) -or [string]::IsNullOrWhiteSpace([string]$final.$field)) {
            throw "missing FINAL field: $field"
        }
    }
    $closed=0; $rows=0
    if (-not [int]::TryParse([string]$final.trades_closed,[ref]$closed)) { throw 'invalid trades_closed.' }
    if (-not [int]::TryParse([string]$final.csv_trade_rows,[ref]$rows)) { throw 'invalid csv_trade_rows.' }
    if ($closed -ne $rows) { throw "counter mismatch: trades_closed=$closed csv_trade_rows=$rows" }
    if ($final.PSObject.Properties.Name -contains 'trades_opened') {
        $opened=0
        if (-not [int]::TryParse([string]$final.trades_opened,[ref]$opened)) { throw 'invalid trades_opened.' }
        if ($opened -ne $closed) { throw "counter mismatch: trades_opened=$opened trades_closed=$closed" }
    }
    $trades = @(Import-Csv -LiteralPath $TradesPath -Delimiter ';')
    if ($trades.Count -ne $closed) { throw "TRADES row mismatch: rows=$($trades.Count) trades_closed=$closed" }
    return [pscustomobject]@{ Final=$final; Trades=$trades; TradesClosed=$closed }
}

function Copy-PublicSafeSnapshot([string]$Source,[string]$Destination,[switch]$RedactWindowsUserPath) {
    Ensure-Parent $Destination
    $raw = Get-Content -LiteralPath $Source -Raw
    if ($RedactWindowsUserPath) {
        $raw=[regex]::Replace($raw,'(?i)([A-Z]:\\Users\\)[^\\;,"\r\n]+','$1<REDACTED>')
    }
    foreach ($rx in @('(?i)password','(?i)api[_-]?key','(?i)secret','(?i)credential','(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}')) {
        if ($raw -match $rx) { throw "PUBLICSAFE block: $([IO.Path]::GetFileName($Source))" }
    }
    if ($raw -match '(?i)[A-Z]:\\Users\\(?!<REDACTED>)[^\\;,"\r\n]+') {
        throw "PUBLICSAFE block: unredacted user path in $([IO.Path]::GetFileName($Source))"
    }
    Set-Content -LiteralPath $Destination -Value $raw -Encoding UTF8
}

function Publish-Pair([IO.FileInfo]$StatsFile,[string]$TradesPath,$State) {
    $statsPath = $StatsFile.FullName
    $sig1 = (Get-StableSignature $statsPath) + '|' + (Get-StableSignature $TradesPath)
    Start-Sleep -Seconds $StableSeconds
    $sig2 = (Get-StableSignature $statsPath) + '|' + (Get-StableSignature $TradesPath)
    if ($sig1 -ne $sig2) { return $false }

    $statsHash1 = Get-Hash $statsPath
    $tradesHash1 = Get-Hash $TradesPath
    $validated = Validate-Pair $statsPath $TradesPath
    if ($statsHash1 -ne (Get-Hash $statsPath) -or $tradesHash1 -ne (Get-Hash $TradesPath)) {
        throw 'outputs changed during validation.'
    }

    $fingerprint = Get-Fingerprint $statsPath $TradesPath
    if (Is-Published $State $fingerprint) { return $false }

    Ensure-ResultsClone
    $familyMatch = [regex]::Match($StatsFile.Name,'^(D\d{3})_')
    $family = if ($familyMatch.Success) { $familyMatch.Groups[1].Value } else { 'DXXX' }
    $symbol = ([string]$validated.Final.symbol -replace '[^A-Za-z0-9_-]','_')
    $stamp = $StatsFile.LastWriteTimeUtc.ToString('yyyyMMdd_HHmmss')
    $runId = "${stamp}_${family}_${symbol}_$($fingerprint.Substring(0,12))"
    $rel = 'backtests/inbox/{0}/{1}/{2}/{3}' -f $StatsFile.LastWriteTimeUtc.ToString('yyyy'),$StatsFile.LastWriteTimeUtc.ToString('MM'),$StatsFile.LastWriteTimeUtc.ToString('dd'),$runId
    $dest = Join-Path $ResultsClone ($rel -replace '/','\')
    $manifestPath = Join-Path $dest 'sync_manifest.json'

    if (Test-Path -LiteralPath $manifestPath) {
        try {
            $old = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            if ($old.fingerprint -eq $fingerprint) {
                Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null
                Mark-Published $State $fingerprint
                Write-Health 'OK' "Recovered existing publication $runId" $StatsFile.Name
                return $false
            }
        } catch {}
        throw "deterministic run path collision: $rel"
    }

    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $statsDest = Join-Path $dest $StatsFile.Name
    $tradesDest = Join-Path $dest ([IO.Path]::GetFileName($TradesPath))
    Copy-PublicSafeSnapshot $statsPath $statsDest -RedactWindowsUserPath
    Copy-PublicSafeSnapshot $TradesPath $tradesDest
    $published = Validate-Pair $statsDest $tradesDest
    $stage = if ($validated.Final.PSObject.Properties.Name -contains 'run_stage') { [string]$validated.Final.run_stage } else { '' }

    [ordered]@{
        schema=5
        run_id=$runId
        fingerprint=$fingerprint
        synced_at_utc=[DateTime]::UtcNow.ToString('o')
        reason='GENERIC_FINAL_VALIDATED'
        branch=$ResultsBranch
        autosync_version='2.02'
        validation=[ordered]@{
            required_status_sequence='INIT -> READY -> FINAL'
            source_name=[string]$validated.Final.source_name
            source_version=[string]$validated.Final.source_version
            run_stage=$stage
            symbol=[string]$validated.Final.symbol
            timeframe=[string]$validated.Final.timeframe
            trades_closed=$published.TradesClosed
            published_trades_rows=$published.Trades.Count
        }
        files=@(
            [ordered]@{name=$StatsFile.Name;source_sha256=$statsHash1;published_sha256=(Get-Hash $statsDest);sanitized=$true},
            [ordered]@{name=[IO.Path]::GetFileName($TradesPath);source_sha256=$tradesHash1;published_sha256=(Get-Hash $tradesDest);sanitized=$false}
        )
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    [ordered]@{
        schema=5
        synced_at_utc=[DateTime]::UtcNow.ToString('o')
        run_id=$runId
        path=$rel
        fingerprint=$fingerprint
        reason='GENERIC_FINAL_VALIDATED'
        files=@($StatsFile.Name,[IO.Path]::GetFileName($TradesPath),'sync_manifest.json')
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $ResultsClone 'backtests\inbox\LATEST.json') -Encoding UTF8

    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'config','user.name','Guardian Backtest Bot') | Out-Null
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'config','user.email','guardian-backtest@local') | Out-Null
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'add','backtests/inbox') | Out-Null
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'commit','-m',"Auto-sync validated $family CSV $runId") | Out-Null
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null

    Mark-Published $State $fingerprint
    Write-Health 'OK' "PUSH OK $runId" $StatsFile.Name
    Write-Log "PUSH OK | $runId | source=$($validated.Final.source_name) | rows=$($validated.TradesClosed)"
    return $true
}

function Invoke-Cycle {
    $state = Load-State

    # Recovery rule: D023 legacy outputs are intentionally left to the already-proven v1.04 lineage.
    # All other finalized Dxxx pairs currently present are eligible, so a completed D036 smoke is recovered
    # even when v2.02 is installed after the test finished.
    $statsFiles = @(Get-ChildItem -LiteralPath $CommonFiles -File -Filter 'D*_STATS.csv' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^D\d{3}_V.+_STATS\.csv$' -and $_.Name -notmatch '^D023_' } |
        Sort-Object LastWriteTimeUtc)

    if ($statsFiles.Count -eq 0) {
        Write-Health 'WAITING_OUTPUTS' 'No eligible Dxxx STATS/TRADES pair present.'
        return
    }

    $publishedAny = $false
    foreach ($statsFile in $statsFiles) {
        $tradesName = $statsFile.Name -replace '_STATS\.csv$','_TRADES.csv'
        $tradesPath = Join-Path $CommonFiles $tradesName
        if (-not (Test-Path -LiteralPath $tradesPath)) { continue }

        try {
            $tail = Get-Content -LiteralPath $statsFile.FullName -Tail 12
            if ($tail -notmatch '(^|;)FINAL(;|$)') { continue }
            if (Publish-Pair $statsFile $tradesPath $state) { $publishedAny = $true }
        } catch {
            $m=$_.Exception.Message
            Write-Log "ERROR cycle | $($statsFile.Name) | $m"
            Write-Health 'ERROR_RETRYING' $m $statsFile.Name
        }
    }

    if (-not $publishedAny) {
        Write-Health 'WAITING_NEW_FINAL' 'Eligible pairs scanned; no unpublished finalized pair found.'
    }
}

function Stop-WatcherPid([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        try {
            $n=0
            $t=(Get-Content -LiteralPath $Path -Raw).Trim()
            if ([int]::TryParse($t,[ref]$n)) { Stop-Process -Id $n -Force -ErrorAction SilentlyContinue }
        } catch {}
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
}

function Stop-OldWatchers {
    foreach ($p in $OldPid) { Stop-WatcherPid $p }
    Remove-Item -LiteralPath $OldStartup -Force -ErrorAction SilentlyContinue
}

function Install-Agent {
    Stop-OldWatchers
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Ensure-Parent $LogFile
    Copy-Item -LiteralPath $PSCommandPath -Destination $InstalledFile -Force
    New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null

    # Same launch pattern as runtime-validated D023 v1.04.
    $cmd='@echo off'+"`r`n"+'start "Guardian Backtest CSV Sync v2.02" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$InstalledFile+'"'+"`r`n"
    Set-Content -LiteralPath $StartupCmd -Value $cmd -Encoding ASCII
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$InstalledFile`"")

    Write-Host "INSTALLE: $InstalledFile"
    Write-Host "AUTOSTART: $StartupCmd"
    Write-Host "HEALTH: $HealthFile"
    Write-Host "LOG: $LogFile"
}

function Uninstall-Agent {
    Stop-WatcherPid $PidFile
    Remove-Item -LiteralPath $StartupCmd -Force -ErrorAction SilentlyContinue
    Write-Host 'Guardian generic AutoSync v2.02 desactive.'
}

if ($Install) { Install-Agent; exit 0 }
if ($Uninstall) { Uninstall-Agent; exit 0 }

# IMPORTANT: Local mutex, matching the proven v1.04 lifecycle. Do not change to Global.
$created=$false
$mutex=New-Object System.Threading.Mutex($true,'Local\GuardianBacktestCsvAutoSyncV202GenericPublicSafe',[ref]$created)
if (-not $created) { exit 0 }

Ensure-Parent $PidFile
Set-Content -LiteralPath $PidFile -Value $PID -Encoding ASCII

try {
    Write-Log "$TaskLabel START | pid=$PID | common=$CommonFiles | stable=${StableSeconds}s"
    Write-Health 'STARTING' 'Generic watcher started; recovering existing finalized non-D023 pairs.'

    while ($true) {
        try { Invoke-Cycle }
        catch {
            $m=$_.Exception.Message
            Write-Log "ERROR cycle | $m"
            Write-Health 'ERROR_RETRYING' $m
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
