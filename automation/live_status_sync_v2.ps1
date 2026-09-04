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
    Add-Content -Path $LocalLog -Value ('{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message) -Encoding UTF8
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

function Ensure-SyncRepo {
    $remote = (& git -C $MainRepo remote get-url origin 2>$null).Trim()
    if (-not $remote) { throw 'Cannot resolve Guardian GitHub origin.' }

    if (-not (Test-Path (Join-Path $SyncRepo '.git'))) {
        if (Test-Path $SyncRepo) { Remove-Item -Recurse -Force $SyncRepo }
        & git clone --quiet $remote $SyncRepo
        if ($LASTEXITCODE -ne 0) { throw 'git clone failed.' }
    }

    & git -C $SyncRepo fetch --quiet origin $Branch 2>$null
    if ($LASTEXITCODE -eq 0) {
        & git -C $SyncRepo checkout -q -B $Branch "origin/$Branch"
    } else {
        & git -C $SyncRepo checkout -q -B $Branch
    }
    if ($LASTEXITCODE -ne 0) { throw 'Cannot checkout live-status branch.' }
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
    } catch {
        return [ordered]@{ state='NOT_FOUND'; last_run=$null; last_result=$null }
    }
}

function Get-BridgeSnapshot {
    $out = @()
    foreach ($r in (Import-SafeCsv $BridgeFile)) {
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
    $tail = @(Get-Content -Path $RuntimeLog -Tail 250 -ErrorAction SilentlyContinue)
    $bad = @($tail | Where-Object { $_ -match '\[MULTIVENUE\]\[REVIEW\]|\[AUTOSTART\]\[(FATAL|EXCEPTION)\]' })
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
        $lastEvent = [ordered]@{ utc=$e.utc_text; event_id=$e.event_id; symbol=$e.symbol; level=$e.level_family; side=$e.side; transition=$e.transition }
    }

    $completed48 = @{}
    foreach ($o in $outcomes) {
        if ($o.horizon -eq '48H' -and $o.event_id) { $completed48[$o.event_id] = $true }
    }

    $openTrades = @()
    foreach ($t in $trades) {
        if ($t.event_id -and -not $completed48.ContainsKey($t.event_id)) {
            $openTrades += [ordered]@{ event_id=$t.event_id; symbol=$t.symbol; side=$t.side; level=$t.level_family; entry_utc=$t.entry_utc_text; entry=$t.entry; virtual_sl=$t.virtual_sl; risk=$t.risk }
        }
    }

    $recentEvents = @()
    foreach ($e in (Last-N $events 12)) {
        $recentEvents += [ordered]@{ utc=$e.utc_text; event_id=$e.event_id; symbol=$e.symbol; level=$e.level_family; side=$e.side; transition=$e.transition }
    }

    $recentOutcomes = @()
    foreach ($o in (Last-N $outcomes 8)) {
        $recentOutcomes += [ordered]@{ utc=$o.utc_text; event_id=$o.event_id; symbol=$o.symbol; side=$o.side; horizon=$o.horizon; mfe_r=$o.mfe_r; mae_r=$o.mae_r; stop_utc=$o.stop_utc; ambiguous_same_m1=$o.ambiguous_same_m1 }
    }

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
            scheduled_task = Get-TaskSnapshot
            bridge = @(Get-BridgeSnapshot)
            last_runtime_alert = Get-RuntimeAlert
        }
    }
}

function Fingerprint($Status) {
    $stableBridge = @()
    foreach ($r in $Status.shared_intelligence.bridge) {
        $stableBridge += [ordered]@{
            symbol=$r.symbol
            bridge_schema_version=$r.bridge_schema_version
            bybit_status=$r.bybit_status
            binance_status=$r.binance_status
            both_core_ok=$r.both_core_ok
        }
    }
    $stable = [ordered]@{
        d025 = $Status.d025
        shared_intelligence = [ordered]@{
            task_state = $Status.shared_intelligence.scheduled_task.state
            task_last_result = $Status.shared_intelligence.scheduled_task.last_result
            bridge_status = $stableBridge
            last_runtime_alert = $Status.shared_intelligence.last_runtime_alert
        }
    }
    return ($stable | ConvertTo-Json -Depth 20 -Compress)
}

function Load-LocalState {
    if (-not (Test-Path $LocalStateFile)) { return $null }
    try { return (Get-Content $LocalStateFile -Raw | ConvertFrom-Json) } catch { return $null }
}

function Save-LocalState($Status) {
    [ordered]@{
        saved_at_utc = [DateTime]::UtcNow.ToString('o')
        fingerprint = Fingerprint $Status
        last_event_id = if ($Status.d025.last_event) { $Status.d025.last_event.event_id } else { $null }
        last_transition = if ($Status.d025.last_event) { $Status.d025.last_event.transition } else { $null }
        last_runtime_alert = $Status.shared_intelligence.last_runtime_alert
    } | ConvertTo-Json -Depth 20 | Set-Content -Path $LocalStateFile -Encoding UTF8
}

function Push-Status($Status) {
    Ensure-SyncRepo
    $target = Join-Path $SyncRepo $StatusFileName
    $Status | ConvertTo-Json -Depth 20 | Set-Content -Path $target -Encoding UTF8
    & git -C $SyncRepo add -- $StatusFileName
    $changed = (& git -C $SyncRepo status --porcelain -- $StatusFileName)
    if (-not $changed) { return }

    & git -C $SyncRepo rev-parse --verify HEAD *> $null
    $hasHead = ($LASTEXITCODE -eq 0)
    if ($hasHead) {
        & git -C $SyncRepo -c user.name='Guardian Live Sync' -c user.email='guardian-live-sync@local' commit -q --amend --no-edit
    } else {
        & git -C $SyncRepo -c user.name='Guardian Live Sync' -c user.email='guardian-live-sync@local' commit -q -m 'Guardian live research status'
    }
    if ($LASTEXITCODE -ne 0) { throw 'git commit/amend failed.' }

    & git -C $SyncRepo push --quiet --force-with-lease origin "HEAD:$Branch"
    if ($LASTEXITCODE -ne 0) { throw 'git push live-status failed.' }
}

function Sync([bool]$Force) {
    try {
        $status = Build-Status
        $previous = Load-LocalState
        $newFp = Fingerprint $status
        $changed = ($null -eq $previous -or [string]$previous.fingerprint -ne $newFp)
        if ($Force -or $changed) {
            Push-Status $status
            Save-LocalState $status
            Log '[SYNC] live-status updated.'
        }
    } catch {
        Log "[ERROR] $($_.Exception.Message)"
        if ($Once) { throw }
    }
}

if ($Once) {
    Sync $true
    exit 0
}

Log '[START] Guardian live-status watcher v2 started.'
$lastHeartbeat = [DateTime]::UtcNow.AddMinutes(-$HeartbeatMinutes)
$lastEventsStamp = [DateTime]::MinValue
$lastTradesStamp = [DateTime]::MinValue
$lastOutcomesStamp = [DateTime]::MinValue
$lastRuntimeStamp = [DateTime]::MinValue

while ($true) {
    $now = [DateTime]::UtcNow
    $heartbeat = (($now - $lastHeartbeat).TotalMinutes -ge $HeartbeatMinutes)
    if ($heartbeat) { $lastHeartbeat = $now }

    $eventsStamp = if (Test-Path $EventsFile) { (Get-Item $EventsFile).LastWriteTimeUtc } else { [DateTime]::MinValue }
    $tradesStamp = if (Test-Path $TradesFile) { (Get-Item $TradesFile).LastWriteTimeUtc } else { [DateTime]::MinValue }
    $outcomesStamp = if (Test-Path $OutcomesFile) { (Get-Item $OutcomesFile).LastWriteTimeUtc } else { [DateTime]::MinValue }
    $runtimeStamp = if (Test-Path $RuntimeLog) { (Get-Item $RuntimeLog).LastWriteTimeUtc } else { [DateTime]::MinValue }

    $sourceChanged = ($eventsStamp -gt $lastEventsStamp -or $tradesStamp -gt $lastTradesStamp -or $outcomesStamp -gt $lastOutcomesStamp -or $runtimeStamp -gt $lastRuntimeStamp)
    if ($sourceChanged -or $heartbeat) { Sync $heartbeat }

    $lastEventsStamp = $eventsStamp
    $lastTradesStamp = $tradesStamp
    $lastOutcomesStamp = $outcomesStamp
    $lastRuntimeStamp = $runtimeStamp
    Start-Sleep -Seconds 20
}
