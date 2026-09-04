param(
    [switch]$Once,
    [int]$HeartbeatMinutes = 15
)

$ErrorActionPreference = 'Stop'

$MainRepo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$SyncRepo = 'D:\MT5_Backtests\guardian-live-status'
$Branch = 'live-status'
$StatusFileName = 'LIVE_RESEARCH_STATUS.json'
$CommonFiles = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$D025Dir = Join-Path $CommonFiles 'GuardianResearch\D025'
$EventsFile = Join-Path $D025Dir 'd025_ler_v0_events.csv'
$TradesFile = Join-Path $D025Dir 'd025_ler_v0_virtual_trades.csv'
$OutcomesFile = Join-Path $D025Dir 'd025_ler_v0_outcomes.csv'
$BridgeFile = Join-Path $CommonFiles 'GuardianSharedIntelligence\market_state_multivenue_v1.csv'
$RuntimeLog = 'D:\MT5_Backtests\Research\ExternalIntelligence\logs\shared_multivenue_autostart_v1.log'
$TaskName = 'Guardian Shared Intelligence MultiVenue V1'
$LocalStateDir = 'D:\MT5_Backtests\Research\LiveStatusSync'
$LocalStateFile = Join-Path $LocalStateDir 'last_sync_state.json'
$LocalLog = Join-Path $LocalStateDir 'live_status_sync.log'

New-Item -ItemType Directory -Force -Path $LocalStateDir | Out-Null

function Log([string]$Message) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -Path $LocalLog -Value $line -Encoding UTF8
}

function Get-RemoteUrl {
    $url = (& git -C $MainRepo remote get-url origin 2>$null)
    if (-not $url) { throw 'Cannot resolve origin remote from main Guardian repository.' }
    return $url.Trim()
}

function Ensure-SyncRepo {
    $remote = Get-RemoteUrl
    if (-not (Test-Path (Join-Path $SyncRepo '.git'))) {
        if (Test-Path $SyncRepo) { Remove-Item -Recurse -Force $SyncRepo }
        & git clone --quiet $remote $SyncRepo
        if ($LASTEXITCODE -ne 0) { throw 'git clone for live-status repo failed.' }
    }

    & git -C $SyncRepo fetch --quiet origin $Branch 2>$null
    if ($LASTEXITCODE -eq 0) {
        & git -C $SyncRepo checkout -q -B $Branch "origin/$Branch"
        if ($LASTEXITCODE -ne 0) { throw 'Cannot checkout live-status branch.' }
    }
    else {
        & git -C $SyncRepo checkout -q -B $Branch
        if ($LASTEXITCODE -ne 0) { throw 'Cannot create live-status branch locally.' }
    }
}

function Import-SafeCsv([string]$Path) {
    if (-not (Test-Path $Path)) { return @() }
    try { return @(Import-Csv -Path $Path -Delimiter ';') }
    catch { Log "[REVIEW] CSV parse failed: $Path :: $($_.Exception.Message)"; return @() }
}

function Last-N($Rows, [int]$N) {
    if ($null -eq $Rows -or $Rows.Count -eq 0) { return @() }
    $start = [Math]::Max(0, $Rows.Count - $N)
    return @($Rows[$start..($Rows.Count-1)])
}

function Get-TaskSnapshot {
    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
        return [ordered]@{
            state = [string]$task.State
            last_run = if ($info.LastRunTime) { $info.LastRunTime.ToString('o') } else { $null }
            last_result = [int64]$info.LastTaskResult
        }
    }
    catch {
        return [ordered]@{ state='NOT_FOUND'; last_run=$null; last_result=$null }
    }
}

function Get-BridgeSnapshot {
    $rows = Import-SafeCsv $BridgeFile
    $out = @()
    foreach ($r in $rows) {
        $out += [ordered]@{
            symbol = $r.symbol
            generation_id = $r.generation_id
            bridge_schema_version = $r.bridge_schema_version
            bybit_status = $r.bybit_status
            binance_status = $r.binance_status
            both_core_ok = $r.both_core_ok
        }
    }
    return $out
}

function Get-RuntimeAlert {
    if (-not (Test-Path $RuntimeLog)) { return $null }
    $tail = @(Get-Content -Path $RuntimeLog -Tail 200 -ErrorAction SilentlyContinue)
    $bad = @($tail | Where-Object { $_ -match '\[MULTIVENUE\]\[REVIEW\]|\[AUTOSTART\]\[(FATAL|EXCEPTION|STOP)\]' })
    if ($bad.Count -eq 0) { return $null }
    return $bad[-1]
}

function Build-Status {
    $events = Import-SafeCsv $EventsFile
    $trades = Import-SafeCsv $TradesFile
    $outcomes = Import-SafeCsv $OutcomesFile

    $lastEvent = $null
    if ($events.Count -gt 0) {
        $e = $events[-1]
        $lastEvent = [ordered]@{
            utc = $e.utc_text
            event_id = $e.event_id
            symbol = $e.symbol
            level = $e.level_family
            side = $e.side
            transition = $e.transition
        }
    }

    $completed48 = @{}
    foreach ($o in $outcomes) {
        if ($o.horizon -eq '48H' -and $o.event_id) { $completed48[$o.event_id] = $true }
    }
    $openTrades = @()
    foreach ($t in $trades) {
        if ($t.event_id -and -not $completed48.ContainsKey($t.event_id)) {
            $openTrades += [ordered]@{
                event_id = $t.event_id
                symbol = $t.symbol
                side = $t.side
                level = $t.level_family
                entry_utc = $t.entry_utc_text
                entry = $t.entry
                virtual_sl = $t.virtual_sl
                risk = $t.risk
            }
        }
    }

    $recentEvents = @()
    foreach ($e in (Last-N $events 12)) {
        $recentEvents += [ordered]@{
            utc = $e.utc_text
            event_id = $e.event_id
            symbol = $e.symbol
            level = $e.level_family
            side = $e.side
            transition = $e.transition
        }
    }

    $recentOutcomes = @()
    foreach ($o in (Last-N $outcomes 8)) {
        $recentOutcomes += [ordered]@{
            utc = $o.utc_text
            event_id = $o.event_id
            symbol = $o.symbol
            side = $o.side
            horizon = $o.horizon
            mfe_r = $o.mfe_r
            mae_r = $o.mae_r
            stop_utc = $o.stop_utc
            ambiguous_same_m1 = $o.ambiguous_same_m1
        }
    }

    $runtimeTask = Get-TaskSnapshot
    $runtimeAlert = Get-RuntimeAlert

    return [ordered]@{
        schema = 1
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
        project = 'Guardian Research / D025 LER'
        source = 'LOCAL_MT5_FORWARD_OBSERVER'
        d025 = [ordered]@{
            mt5_version = '1.00'
            research_generation = 'V0'
            signals_are_virtual_only = $true
            event_count = $events.Count
            virtual_trade_count_total = $trades.Count
            virtual_trades_open = $openTrades
            last_event = $lastEvent
            recent_events = $recentEvents
            recent_outcomes = $recentOutcomes
        }
        shared_intelligence = [ordered]@{
            scheduled_task = $runtimeTask
            bridge = @(Get-BridgeSnapshot)
            last_runtime_alert = $runtimeAlert
        }
    }
}

function Load-LastState {
    if (-not (Test-Path $LocalStateFile)) { return $null }
    try { return (Get-Content $LocalStateFile -Raw | ConvertFrom-Json) }
    catch { return $null }
}

function Save-LastState($Obj) {
    $Obj | ConvertTo-Json -Depth 20 | Set-Content -Path $LocalStateFile -Encoding UTF8
}

function Meaningful-Fingerprint($Status) {
    $copy = [ordered]@{
        d025 = $Status.d025
        shared_intelligence = $Status.shared_intelligence
    }
    return ($copy | ConvertTo-Json -Depth 20 -Compress)
}

function Should-Sync($Status, $Previous, [bool]$ForceHeartbeat) {
    if ($null -eq $Previous) { return $true }
    $newFp = Meaningful-Fingerprint $Status
    $oldFp = [string]$Previous.fingerprint
    if ($newFp -ne $oldFp) { return $true }
    if ($ForceHeartbeat) { return $true }
    return $false
}

function Push-LiveStatus($Status) {
    Ensure-SyncRepo
    $target = Join-Path $SyncRepo $StatusFileName
    $Status | ConvertTo-Json -Depth 20 | Set-Content -Path $target -Encoding UTF8

    & git -C $SyncRepo add -- $StatusFileName
    $changed = (& git -C $SyncRepo status --porcelain -- $StatusFileName)
    if (-not $changed) { return }

    $hasHead = $true
    & git -C $SyncRepo rev-parse --verify HEAD *> $null
    if ($LASTEXITCODE -ne 0) { $hasHead = $false }

    if ($hasHead) {
        & git -C $SyncRepo commit -q --amend --no-edit
    }
    else {
        & git -C $SyncRepo -c user.name='Guardian Live Sync' -c user.email='guardian-live-sync@local' commit -q -m 'Guardian live research status'
    }
    if ($LASTEXITCODE -ne 0) { throw 'git commit/amend failed.' }

    & git -C $SyncRepo push --quiet --force-with-lease origin "HEAD:$Branch"
    if ($LASTEXITCODE -ne 0) { throw 'git push live-status failed.' }
}

function Run-Sync([bool]$ForceHeartbeat) {
    try {
        $status = Build-Status
        $previous = Load-LastState
        if (Should-Sync $status $previous $ForceHeartbeat) {
            Push-LiveStatus $status
            $state = [ordered]@{
                saved_at_utc = [DateTime]::UtcNow.ToString('o')
                fingerprint = Meaningful-Fingerprint $status
                last_event_id = if ($status.d025.last_event) { $status.d025.last_event.event_id } else { $null }
                last_transition = if ($status.d025.last_event) { $status.d025.last_event.transition } else { $null }
                last_runtime_alert = $status.shared_intelligence.last_runtime_alert
            }
            Save-LastState $state
            Log '[SYNC] live-status updated.'
        }
    }
    catch {
        Log "[ERROR] $($_.Exception.Message)"
    }
}

if ($Once) {
    Run-Sync $true
    exit 0
}

Log '[START] Guardian live-status watcher started.'
$lastHeartbeat = [DateTime]::UtcNow.AddMinutes(-$HeartbeatMinutes)
$lastEventFileStamp = [DateTime]::MinValue
$lastTradeFileStamp = [DateTime]::MinValue
$lastRuntimeLogStamp = [DateTime]::MinValue

while ($true) {
    $force = $false
    $now = [DateTime]::UtcNow
    if (($now - $lastHeartbeat).TotalMinutes -ge $HeartbeatMinutes) {
        $force = $true
        $lastHeartbeat = $now
    }

    $eventStamp = if (Test-Path $EventsFile) { (Get-Item $EventsFile).LastWriteTimeUtc } else { [DateTime]::MinValue }
    $tradeStamp = if (Test-Path $TradesFile) { (Get-Item $TradesFile).LastWriteTimeUtc } else { [DateTime]::MinValue }
    $runtimeStamp = if (Test-Path $RuntimeLog) { (Get-Item $RuntimeLog).LastWriteTimeUtc } else { [DateTime]::MinValue }

    $eventChanged = $eventStamp -gt $lastEventFileStamp
    $tradeChanged = $tradeStamp -gt $lastTradeFileStamp
    $runtimeChanged = $runtimeStamp -gt $lastRuntimeLogStamp

    if ($eventChanged -or $tradeChanged -or $runtimeChanged -or $force) {
        $previous = Load-LastState
        $status = Build-Status
        $urgent = $false
        if ($status.d025.last_event -and $status.d025.last_event.transition -like 'VALID_SIGNAL*') {
            if ($null -eq $previous -or $previous.last_event_id -ne $status.d025.last_event.event_id -or $previous.last_transition -ne $status.d025.last_event.transition) {
                $urgent = $true
            }
        }
        if ($status.shared_intelligence.last_runtime_alert) {
            if ($null -eq $previous -or $previous.last_runtime_alert -ne $status.shared_intelligence.last_runtime_alert) {
                $urgent = $true
            }
        }

        if ($urgent -or $force) {
            Run-Sync $true
        }
        else {
            # For ordinary D025 state changes, sync immediately too, but only when the meaningful payload changed.
            Run-Sync $false
        }
    }

    $lastEventFileStamp = $eventStamp
    $lastTradeFileStamp = $tradeStamp
    $lastRuntimeLogStamp = $runtimeStamp
    Start-Sleep -Seconds 20
}
