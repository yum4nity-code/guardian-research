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

$TaskLabel      = 'Guardian D023 CSV AutoSync v1.04 NATIVEGITFIX PUBLICSAFE'
$InstallDir     = 'D:\MT5_Backtests\automation'
$InstalledFile  = Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v1_04_D023_NATIVEGITFIX_PUBLICSAFE.ps1'
$StartupDir     = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd     = Join-Path $StartupDir 'Guardian_D023_CSV_AutoSync_v1_04.cmd'
$OldStartupV103 = Join-Path $StartupDir 'Guardian_D023_CSV_AutoSync_v1_03.cmd'
$OldStartupV102 = Join-Path $StartupDir 'Guardian_D023_CSV_AutoSync_v1_02.cmd'
$PidFile        = 'D:\MT5_Backtests\guardian-d023-csv-sync-v104.pid'
$OldPidV103     = 'D:\MT5_Backtests\guardian-d023-csv-sync-v103.pid'
$OldPidV102     = 'D:\MT5_Backtests\guardian-d023-csv-sync-v102.pid'
$StateFile      = 'D:\MT5_Backtests\guardian-d023-csv-sync-v104-state.json'
$HealthFile     = 'D:\MT5_Backtests\guardian-d023-csv-sync-v104-health.json'
$LogFile        = 'D:\MT5_Backtests\logs\guardian-d023-csv-sync-v104.log'
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
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
}

function Write-Log([string]$Message) {
    Ensure-Parent $LogFile
    $line = ('{0} | {1}' -f ([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')), $Message)
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    if (-not $Install) { Write-Host $line }
}

function Write-Health([string]$Status,[string]$Message,[string]$Fingerprint='') {
    Ensure-Parent $HealthFile
    [ordered]@{
        schema=1; watcher=$TaskLabel; updated_at_utc=[DateTime]::UtcNow.ToString('o'); status=$Status; message=$Message;
        fingerprint=$Fingerprint; common_files=$CommonFiles; stats_name=$StatsName; trades_name=$TradesName; results_branch=$ResultsBranch
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$HealthFile.tmp" -Encoding UTF8
    Move-Item -LiteralPath "$HealthFile.tmp" -Destination $HealthFile -Force
}

function Quote-NativeArg([string]$Value) {
    if ($null -eq $Value -or $Value.Length -eq 0) { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + ($Value -replace '(\\*)"','$1$1\"' -replace '(\\+)$','$1$1') + '"'
}

# Uses Start-Process redirection so normal git stderr (fetch/pull progress) is never promoted
# to a terminating PowerShell error under Windows PowerShell 5.1.
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
        if ($i -ge $attempts) { throw "git $($GitArgs -join ' ') failed after $attempts attempts: $($r.Output -join ' ')" }
        $delay = [Math]::Min(60,[Math]::Pow(2,$i))
        Write-Log "WARN git retry $i/$attempts in ${delay}s | $($GitArgs -join ' ')"
        Start-Sleep -Seconds ([int]$delay)
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
        Ensure-Parent (Join-Path $ResultsClone 'dummy')
        $remote = Get-RemoteUrl
        Write-Log "Clone $ResultsBranch depuis $remote"
        Invoke-GitRetry -GitArgs @('clone','--quiet','--branch',$ResultsBranch,'--single-branch',$remote,$ResultsClone) | Out-Null
    }
    $branch = Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'rev-parse','--abbrev-ref','HEAD')
    $branchName = (($branch.StdOut | Select-Object -First 1).ToString()).Trim()
    if ($branchName -ne $ResultsBranch) { Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'checkout','-q',$ResultsBranch) | Out-Null }
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch) | Out-Null
}

function Get-Hash([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function Get-StableSignature([string]$Path) { $f=Get-Item -LiteralPath $Path; return ('{0}|{1}' -f $f.Length,$f.LastWriteTimeUtc.Ticks) }

function Get-StateFingerprint {
    if (-not (Test-Path -LiteralPath $StateFile)) { return '' }
    try { $o=Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json; if ($o.last_published_fingerprint) { return $o.last_published_fingerprint.ToString() } } catch {}
    return ''
}

function Save-State([string]$Fingerprint,[string]$RunId) {
    Ensure-Parent $StateFile
    [ordered]@{schema=1;updated_at_utc=[DateTime]::UtcNow.ToString('o');last_published_fingerprint=$Fingerprint;last_run_id=$RunId} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$StateFile.tmp" -Encoding UTF8
    Move-Item -LiteralPath "$StateFile.tmp" -Destination $StateFile -Force
}

function Import-D023([string]$StatsPath,[string]$TradesPath) {
    $stats=@(Import-Csv -LiteralPath $StatsPath -Delimiter ';')
    if ($stats.Count -lt 3) { throw 'D023 STATS incomplete.' }
    $statuses=@($stats | ForEach-Object { $_.status })
    $i=[Array]::IndexOf($statuses,'INIT'); $r=[Array]::IndexOf($statuses,'READY'); $f=[Array]::LastIndexOf($statuses,'FINAL')
    if ($i -lt 0 -or $r -lt 0 -or $f -lt 0 -or -not ($i -lt $r -and $r -lt $f)) { throw 'D023 STATS sequence invalid; require INIT -> READY -> FINAL.' }
    $final=$stats[$f]
    if ($final.source_name -ne $ExpectedSource) { throw "unexpected source_name: $($final.source_name)" }
    if ($final.source_version -ne $ExpectedVer) { throw "unexpected source_version: $($final.source_version)" }
    if ($final.symbol -notmatch 'USDJPY') { throw "unexpected symbol: $($final.symbol)" }
    if ($final.timeframe -ne 'PERIOD_M15') { throw "unexpected timeframe: $($final.timeframe)" }
    $closed=0; $csvRows=0
    if (-not [int]::TryParse($final.trades_closed,[ref]$closed)) { throw 'invalid trades_closed.' }
    if (-not [int]::TryParse($final.csv_trade_rows,[ref]$csvRows)) { throw 'invalid csv_trade_rows.' }
    if ($closed -ne $csvRows) { throw "counter mismatch: trades_closed=$closed csv_trade_rows=$csvRows" }
    $trades=@(Import-Csv -LiteralPath $TradesPath -Delimiter ';')
    if ($trades.Count -ne $closed) { throw "TRADES row mismatch: rows=$($trades.Count) trades_closed=$closed" }
    return [pscustomobject]@{Stats=$stats;Final=$final;Trades=$trades;TradesClosed=$closed}
}

function Copy-PublicSafeSnapshot([string]$Source,[string]$Destination,[switch]$RedactWindowsUserPath) {
    Ensure-Parent $Destination
    $raw=Get-Content -LiteralPath $Source -Raw
    if ($RedactWindowsUserPath) { $raw=[regex]::Replace($raw,'(?i)([A-Z]:\\Users\\)[^\\;,"\r\n]+','$1<REDACTED>') }
    foreach ($rx in @('(?i)password','(?i)api[_-]?key','(?i)secret','(?i)credential','(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}')) {
        if ($raw -match $rx) { throw "PUBLICSAFE block: $([IO.Path]::GetFileName($Source))" }
    }
    if ($raw -match '(?i)[A-Z]:\\Users\\(?!<REDACTED>)[^\\;,"\r\n]+') { throw "PUBLICSAFE block: unredacted user path in $([IO.Path]::GetFileName($Source))" }
    Set-Content -LiteralPath $Destination -Value $raw -Encoding UTF8
}

function Publish-D023([string]$StatsPath,[string]$TradesPath) {
    $sh1=Get-Hash $StatsPath; $th1=Get-Hash $TradesPath
    $validated=Import-D023 -StatsPath $StatsPath -TradesPath $TradesPath
    $sh2=Get-Hash $StatsPath; $th2=Get-Hash $TradesPath
    if ($sh1 -ne $sh2 -or $th1 -ne $th2) { throw 'D023 outputs changed during validation.' }
    $si=Get-Item -LiteralPath $StatsPath; $ti=Get-Item -LiteralPath $TradesPath
    $seed="$StatsName|$($si.LastWriteTimeUtc.Ticks)|$sh2|$TradesName|$($ti.LastWriteTimeUtc.Ticks)|$th2"
    $sha=[System.Security.Cryptography.SHA256]::Create()
    try { $fingerprint=(($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($seed)) | ForEach-Object { $_.ToString('x2') }) -join '') } finally { $sha.Dispose() }
    if ((Get-StateFingerprint) -eq $fingerprint) { Write-Health 'OK' 'Current finalized D023 pair already published.' $fingerprint; return $false }

    Ensure-ResultsClone
    $stamp=$si.LastWriteTimeUtc.ToString('yyyyMMdd_HHmmss')
    $runId='{0}_D023_V108_USDJPY_{1}' -f $stamp,$fingerprint.Substring(0,12)
    $rel='backtests/inbox/{0}/{1}/{2}/{3}' -f $si.LastWriteTimeUtc.ToString('yyyy'),$si.LastWriteTimeUtc.ToString('MM'),$si.LastWriteTimeUtc.ToString('dd'),$runId
    $dest=Join-Path $ResultsClone ($rel -replace '/','\'); $manifestPath=Join-Path $dest 'sync_manifest.json'

    if (Test-Path -LiteralPath $manifestPath) {
        try {
            $old=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
            if ($old.fingerprint -eq $fingerprint) {
                Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null
                Save-State $fingerprint $runId; Write-Health 'OK' 'D023 publication already present and pushed.' $fingerprint; return $false
            }
        } catch {}
        throw "deterministic run path collision: $rel"
    }

    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $sd=Join-Path $dest $StatsName; $td=Join-Path $dest $TradesName
    Copy-PublicSafeSnapshot $StatsPath $sd -RedactWindowsUserPath
    Copy-PublicSafeSnapshot $TradesPath $td
    $published=Import-D023 $sd $td

    [ordered]@{
        schema=4; run_id=$runId; fingerprint=$fingerprint; synced_at_utc=$si.LastWriteTimeUtc.ToString('o'); reason='D023_V108_FINAL_VALIDATED';
        branch=$ResultsBranch; autosync_version='1.04'; validation=[ordered]@{required_status_sequence='INIT -> READY -> FINAL';source_name=$ExpectedSource;source_version=$ExpectedVer;symbol=$published.Final.symbol;timeframe=$published.Final.timeframe;trades_closed=$published.TradesClosed;csv_trade_rows=[int]$published.Final.csv_trade_rows;published_trades_rows=$published.Trades.Count};
        files=@([ordered]@{name=$StatsName;source_sha256=$sh2;published_sha256=(Get-Hash $sd);sanitized=$true},[ordered]@{name=$TradesName;source_sha256=$th2;published_sha256=(Get-Hash $td);sanitized=$false})
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $latestPath=Join-Path $ResultsClone 'backtests\inbox\LATEST.json'; Ensure-Parent $latestPath
    [ordered]@{schema=4;synced_at_utc=$si.LastWriteTimeUtc.ToString('o');run_id=$runId;path=$rel;fingerprint=$fingerprint;reason='D023_V108_FINAL_VALIDATED';files=@($StatsName,$TradesName,'sync_manifest.json')} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $latestPath -Encoding UTF8

    Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'add','--',$rel,'backtests/inbox/LATEST.json') | Out-Null
    $c=Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'-c','user.name=Guardian Backtest Bot','-c','user.email=guardian-backtest@local','commit','-m',"Auto-sync validated D023 CSV $runId") -AllowFailure
    if ($c.Code -ne 0) {
        $s=Invoke-GitOnce -GitArgs @('-C',$ResultsClone,'status','--porcelain','--','backtests/inbox')
        if ($s.StdOut.Count -gt 0) { throw "git commit failed: $($c.Output -join ' ')" }
    }
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch) | Out-Null
    Invoke-GitRetry -GitArgs @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null
    Save-State $fingerprint $runId
    Write-Health 'OK' "PUSH OK $rel" $fingerprint
    Write-Log "PUSH OK | D023 FINAL VALIDATED | $rel | trades=$($validated.TradesClosed)"
    return $true
}

function Stop-WatcherPid([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        try { $n=0; $t=(Get-Content -LiteralPath $Path -Raw).Trim(); if ([int]::TryParse($t,[ref]$n)) { Stop-Process -Id $n -Force -ErrorAction SilentlyContinue } } catch {}
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
}

function Stop-OldWatchers {
    Stop-WatcherPid $OldPidV103; Stop-WatcherPid $OldPidV102
    Remove-Item -LiteralPath $OldStartupV103,$OldStartupV102 -Force -ErrorAction SilentlyContinue
}

function Install-Agent {
    Stop-OldWatchers
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null; Ensure-Parent $LogFile
    Copy-Item -LiteralPath $PSCommandPath -Destination $InstalledFile -Force
    New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null
    $cmd='@echo off'+"`r`n"+'start "Guardian D023 CSV Sync v1.04" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$InstalledFile+'"'+"`r`n"
    Set-Content -LiteralPath $StartupCmd -Value $cmd -Encoding ASCII
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$InstalledFile`"")
    Write-Host "INSTALLE: $InstalledFile"; Write-Host "AUTOSTART: $StartupCmd"; Write-Host "HEALTH: $HealthFile"; Write-Host "LOG: $LogFile"
}

function Uninstall-Agent {
    Stop-WatcherPid $PidFile; Remove-Item -LiteralPath $StartupCmd -Force -ErrorAction SilentlyContinue
    Write-Host 'Guardian D023 CSV AutoSync v1.04 desactive.'
}

if ($Install) { Install-Agent; exit 0 }
if ($Uninstall) { Uninstall-Agent; exit 0 }

$created=$false
$mutex=New-Object System.Threading.Mutex($true,'Local\GuardianD023CsvAutoSyncV104NativeGitFixPublicSafe',[ref]$created)
if (-not $created) { exit 0 }
Ensure-Parent $PidFile; Set-Content -LiteralPath $PidFile -Value $PID -Encoding ASCII
$statsPath=Join-Path $CommonFiles $StatsName; $tradesPath=Join-Path $CommonFiles $TradesName
$lastSig=''; $stableSince=[DateTime]::UtcNow
try {
    Write-Log "$TaskLabel START | pid=$PID | common=$CommonFiles | stable=${StableSeconds}s"; Write-Health 'STARTING' 'Waiting for finalized D023 v1.08 outputs.'
    while ($true) {
        try {
            if (-not (Test-Path -LiteralPath $statsPath) -or -not (Test-Path -LiteralPath $tradesPath)) { Write-Health 'WAITING_OUTPUTS' 'D023 STATS/TRADES pair not present yet.' }
            else {
                $sig=(Get-StableSignature $statsPath)+'|'+(Get-StableSignature $tradesPath); $now=[DateTime]::UtcNow
                if ($sig -ne $lastSig) { $lastSig=$sig; $stableSince=$now }
                if ($Once -or (($now-$stableSince).TotalSeconds -ge $StableSeconds)) {
                    $tail=Get-Content -LiteralPath $statsPath -Tail 8
                    if ($tail -match '(^|;)FINAL(;|$)') { [void](Publish-D023 $statsPath $tradesPath) }
                    else { Write-Health 'WAITING_FINAL' 'D023 files exist but STATS FINAL is not present yet.' }
                }
            }
        } catch { $m=$_.Exception.Message; Write-Log "ERROR cycle | $m"; Write-Health 'ERROR_RETRYING' $m }
        if ($Once) { break }
        Start-Sleep -Seconds ([Math]::Max(2,$PollSeconds))
    }
} finally {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    try { $mutex.ReleaseMutex() } catch {}; $mutex.Dispose(); Write-Log "$TaskLabel STOP"
}
