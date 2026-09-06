param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Once,
    [int]$PollSeconds = 5,
    [int]$StableSeconds = 20,
    [int]$RecentMinutes = 30,
    [int]$MaxFileMB = 90,
    [string]$IncludeRegex = '(?i)^(d\d{2,3}|guardian)[_-].*\.csv$'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$TaskLabel      = 'Guardian Backtest CSV AutoSync v1.01 PUBLICSAFE'
$InstallDir     = 'D:\MT5_Backtests\automation'
$InstalledFile  = Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v1_01_PUBLICSAFE.ps1'
$StartupDir     = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd     = Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync.cmd'
$PidFile        = 'D:\MT5_Backtests\guardian-backtest-csv-sync.pid'
$StateFile      = 'D:\MT5_Backtests\guardian-backtest-csv-sync-state.json'
$LogFile        = 'D:\MT5_Backtests\logs\guardian-backtest-csv-sync.log'
$ResultsClone   = 'D:\MT5_Backtests\guardian-backtest-autosync-results'
$ResultsBranch  = 'backtest-results'
$RemoteFallback = 'https://github.com/yum4nity-code/guardian-research.git'
$MaxBytes       = [int64]$MaxFileMB * 1MB

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

function Invoke-Git([string[]]$Args, [switch]$AllowFailure) {
    $output = & git @Args 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "git $($Args -join ' ') failed ($code): $($output -join ' ')"
    }
    return [pscustomobject]@{ Code=$code; Output=$output }
}

function Get-RemoteUrl {
    $candidates = @(
        'D:\MT5_Backtests\guardian-research',
        (Split-Path -Parent $PSScriptRoot)
    ) | Select-Object -Unique

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate '.git'))) {
            try {
                $r = Invoke-Git -Args @('-C',$candidate,'remote','get-url','origin')
                $u = (($r.Output | Select-Object -First 1).ToString()).Trim()
                if ($u) { return $u }
            } catch {}
        }
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
        }
        Ensure-Parent (Join-Path $ResultsClone 'dummy')
        $remote = Get-RemoteUrl
        Write-Log "Clone branche $ResultsBranch depuis $remote"
        Invoke-Git -Args @('clone','--quiet','--branch',$ResultsBranch,'--single-branch',$remote,$ResultsClone) | Out-Null
    }

    Invoke-Git -Args @('-C',$ResultsClone,'fetch','--quiet','origin',$ResultsBranch) | Out-Null
    $branch = Invoke-Git -Args @('-C',$ResultsClone,'rev-parse','--abbrev-ref','HEAD')
    if ((($branch.Output | Select-Object -First 1).ToString()).Trim() -ne $ResultsBranch) {
        Invoke-Git -Args @('-C',$ResultsClone,'checkout','-q',$ResultsBranch) | Out-Null
    }

    # Preserve any previous local commit that failed to push, then reconcile remote.
    $pushTry = Invoke-Git -Args @('-C',$ResultsClone,'push','origin',$ResultsBranch) -AllowFailure
    if ($pushTry.Code -ne 0) {
        Invoke-Git -Args @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch) | Out-Null
        Invoke-Git -Args @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null
    } else {
        Invoke-Git -Args @('-C',$ResultsClone,'pull','--ff-only','origin',$ResultsBranch) | Out-Null
    }
}

function Get-Hash([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Copy-ReadableSnapshot([string]$Source, [string]$Destination) {
    Ensure-Parent $Destination
    $input = New-Object System.IO.FileStream($Source,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
    try {
        $output = New-Object System.IO.FileStream($Destination,[System.IO.FileMode]::Create,[System.IO.FileAccess]::Write,[System.IO.FileShare]::Read)
        try { $input.CopyTo($output) } finally { $output.Dispose() }
    } finally { $input.Dispose() }
}

function Test-StatsFinal([string]$Path) {
    try {
        $tail = Get-Content -LiteralPath $Path -Tail 8 -ErrorAction Stop
        return [bool]($tail | Where-Object { $_ -match '(^|;)FINAL(;|$)' })
    } catch { return $false }
}

function Get-RunPrefix([string]$Name) {
    if ($Name -match '^(.*)_(STATS|TRADES)\.csv$') { return $Matches[1] }
    return [System.IO.Path]::GetFileNameWithoutExtension($Name)
}

function Sanitize-Name([string]$Value) {
    $s = $Value -replace '[^A-Za-z0-9._-]','_'
    if ($s.Length -gt 90) { $s = $s.Substring(0,90) }
    return $s
}

function Test-PublicSafeCsv([System.IO.FileInfo]$File) {
    if ($File.Name -notmatch $IncludeRegex) { return $false }
    try {
        $fs = New-Object System.IO.FileStream($File.FullName,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
        try {
            $max = [Math]::Min([int64]16384,$fs.Length)
            $buf = New-Object byte[] ([int]$max)
            [void]$fs.Read($buf,0,$buf.Length)
            $sample = [System.Text.Encoding]::UTF8.GetString($buf)
        } finally { $fs.Dispose() }
    } catch { return $false }

    $blocked = @(
        '(?i)password',
        '(?i)api[_-]?key',
        '(?i)secret',
        '(?i)credential',
        '(?i)account[_-]?(number|login|id)',
        '(?i)\\Users\\[^;,"]+',
        '(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}'
    )
    foreach ($rx in $blocked) {
        if ($sample -match $rx) {
            Write-Log "BLOCK PUBLIC SAFETY | $($File.Name) | motif sensible detecte"
            return $false
        }
    }
    return $true
}

function Discover-Roots {
    $set = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    $common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
    if (Test-Path -LiteralPath $common) { [void]$set.Add((Resolve-Path $common).Path) }

    foreach ($base in @(
        (Join-Path $env:APPDATA 'MetaQuotes\Terminal'),
        (Join-Path $env:APPDATA 'MetaQuotes\Tester')
    )) {
        if (-not (Test-Path -LiteralPath $base)) { continue }
        try {
            Get-ChildItem -LiteralPath $base -Directory -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -eq 'Files' -and $_.Parent -and $_.Parent.Name -eq 'MQL5' } |
                ForEach-Object { [void]$set.Add($_.FullName) }
        } catch {}
    }

    foreach ($pname in @('terminal64','terminal','metatester64','metatester')) {
        Get-Process -Name $pname -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $exeDir = Split-Path -Parent $_.Path
                foreach ($p in @((Join-Path $exeDir 'MQL5\Files'),(Join-Path $exeDir 'Tester'))) {
                    if (Test-Path -LiteralPath $p) { [void]$set.Add((Resolve-Path $p).Path) }
                }
            } catch {}
        }
    }

    foreach ($p in @(
        'D:\MT5_Backtests\outputs',
        'D:\MT5_Backtests\results',
        'D:\MT5_Backtests\runs',
        'D:\MT5_Backtests\Research\outputs',
        'D:\MT5_Backtests\research\outputs'
    )) {
        if (Test-Path -LiteralPath $p) { [void]$set.Add((Resolve-Path $p).Path) }
    }

    return @($set)
}

function Get-CsvFiles([string[]]$Roots) {
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($root in $Roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        try {
            Get-ChildItem -LiteralPath $root -Filter '*.csv' -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
                if (-not $_.FullName.StartsWith($ResultsClone,[System.StringComparison]::OrdinalIgnoreCase) -and
                    $_.Length -gt 0 -and $_.Length -le $MaxBytes -and
                    (Test-PublicSafeCsv $_)) {
                    if ($seen.Add($_.FullName)) { $_ }
                }
            }
        } catch {
            Write-Log "WARN scan root $root : $($_.Exception.Message)"
        }
    }
}

function Load-State {
    $published = @{}
    if (Test-Path -LiteralPath $StateFile) {
        try {
            $obj = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
            foreach ($h in @($obj.published_sha256)) {
                if ($h) { $published[$h.ToString()] = $true }
            }
        } catch {
            Write-Log "WARN state illisible, nouveau state: $($_.Exception.Message)"
        }
    }
    return $published
}

function Save-State([hashtable]$Published) {
    Ensure-Parent $StateFile
    $obj = [ordered]@{
        schema = 1
        updated_at_utc = [DateTime]::UtcNow.ToString('o')
        published_sha256 = @($Published.Keys | Sort-Object)
    }
    $tmp = "$StateFile.tmp"
    $obj | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $StateFile -Force
}

function Publish-Group([System.IO.FileInfo[]]$Files, [string]$Reason, [hashtable]$Published) {
    if (-not $Files -or $Files.Count -eq 0) { return $false }

    $records = @()
    foreach ($f in ($Files | Sort-Object FullName -Unique)) {
        if (-not (Test-Path -LiteralPath $f.FullName)) { continue }
        $hash = Get-Hash $f.FullName
        if ($Published.ContainsKey($hash)) { continue }
        $records += [pscustomobject]@{ File=$f; Hash=$hash }
    }
    if ($records.Count -eq 0) { return $false }

    Ensure-ResultsClone

    $now = [DateTime]::UtcNow
    $prefix = Sanitize-Name (Get-RunPrefix $records[0].File.Name)
    $finger = $records[0].Hash.Substring(0,10)
    $runId = '{0}_{1}_{2}' -f $now.ToString('yyyyMMdd_HHmmss'),$prefix,$finger
    $rel = 'backtests/inbox/{0}/{1}/{2}/{3}' -f $now.ToString('yyyy'),$now.ToString('MM'),$now.ToString('dd'),$runId
    $dest = Join-Path $ResultsClone ($rel -replace '/','\')
    New-Item -ItemType Directory -Force -Path $dest | Out-Null

    $manifestFiles = @()
    foreach ($r in $records) {
        $target = Join-Path $dest $r.File.Name
        Copy-ReadableSnapshot $r.File.FullName $target
        $snapHash = Get-Hash $target
        if ($snapHash -ne $r.Hash) { throw "Snapshot hash mismatch: $($r.File.FullName)" }
        $manifestFiles += [ordered]@{
            name = $r.File.Name
            size_bytes = (Get-Item -LiteralPath $target).Length
            source_last_write_utc = $r.File.LastWriteTimeUtc.ToString('o')
            sha256 = $r.Hash
        }
    }

    $manifest = [ordered]@{
        schema = 1
        run_id = $runId
        synced_at_utc = $now.ToString('o')
        reason = $Reason
        branch = $ResultsBranch
        files = $manifestFiles
    }
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $dest 'sync_manifest.json') -Encoding UTF8

    $latest = [ordered]@{
        schema = 1
        synced_at_utc = $now.ToString('o')
        run_id = $runId
        path = $rel
        reason = $Reason
        files = @($manifestFiles | ForEach-Object { $_.name })
    }
    $latestPath = Join-Path $ResultsClone 'backtests\inbox\LATEST.json'
    Ensure-Parent $latestPath
    $latest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $latestPath -Encoding UTF8

    Invoke-Git -Args @('-C',$ResultsClone,'add','--',$rel,'backtests/inbox/LATEST.json') | Out-Null
    $commit = Invoke-Git -Args @('-C',$ResultsClone,'-c','user.name=Guardian Backtest Bot','-c','user.email=guardian-backtest@local','commit','-m',"Auto-sync MT5 CSV $runId") -AllowFailure
    if ($commit.Code -ne 0) {
        $status = Invoke-Git -Args @('-C',$ResultsClone,'status','--porcelain')
        if ($status.Output.Count -gt 0) { throw "git commit failed: $($commit.Output -join ' ')" }
        return $false
    }

    Invoke-Git -Args @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch) | Out-Null
    Invoke-Git -Args @('-C',$ResultsClone,'push','origin',$ResultsBranch) | Out-Null

    foreach ($r in $records) { $Published[$r.Hash] = $true }
    Save-State $Published
    Write-Log "PUSH OK | $Reason | $rel | $($records.Count) CSV"
    return $true
}

function Install-Agent {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Ensure-Parent $LogFile
    Copy-Item -LiteralPath $PSCommandPath -Destination $InstalledFile -Force
    New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null

    $cmd = '@echo off' + "`r`n" +
           'start "Guardian CSV Sync" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $InstalledFile + '"' + "`r`n"
    Set-Content -LiteralPath $StartupCmd -Value $cmd -Encoding ASCII

    # Start it now; the named mutex prevents duplicate workers.
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$InstalledFile`"")
    Write-Host "INSTALLE: $InstalledFile"
    Write-Host "AUTOSTART: $StartupCmd"
    Write-Host "LOG: $LogFile"
    Write-Host "GITHUB PUBLIC: seuls les CSV Guardian filtres sont envoyes sur $ResultsBranch / backtests/inbox/"
}

function Uninstall-Agent {
    if (Test-Path -LiteralPath $PidFile) {
        try {
            $pidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
            $workerPid = 0
            if ([int]::TryParse($pidText,[ref]$workerPid)) {
                Stop-Process -Id $workerPid -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
    Remove-Item -LiteralPath $StartupCmd -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host 'Guardian Backtest CSV AutoSync desactive.'
}

if ($Install) { Install-Agent; exit 0 }
if ($Uninstall) { Uninstall-Agent; exit 0 }

# Single-instance worker.
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true,'Local\GuardianBacktestCsvAutoSyncV101PublicSafe',[ref]$createdNew)
if (-not $createdNew) { exit 0 }
Ensure-Parent $PidFile
Set-Content -LiteralPath $PidFile -Value $PID -Encoding ASCII

$published = Load-State
$observed = @{}
$startedUtc = [DateTime]::UtcNow
$lastRootsRefresh = [DateTime]::MinValue
$roots = @()

try {
    Write-Log "$TaskLabel START | pid=$PID | stable=${StableSeconds}s | recent=${RecentMinutes}m | filter=$IncludeRegex"
    while ($true) {
        $now = [DateTime]::UtcNow
        if (($now - $lastRootsRefresh).TotalSeconds -ge 60 -or $roots.Count -eq 0) {
            $roots = @(Discover-Roots)
            $lastRootsRefresh = $now
            Write-Log ('ROOTS ' + ($roots -join ' | '))
        }

        $files = @(Get-CsvFiles $roots)
        foreach ($f in $files) {
            $key = $f.FullName
            $sig = '{0}|{1}' -f $f.Length,$f.LastWriteTimeUtc.Ticks
            if (-not $observed.ContainsKey($key)) {
                $observed[$key] = [ordered]@{ Signature=$sig; StableSince=$now }
                if (($now - $f.LastWriteTimeUtc).TotalMinutes -ge $RecentMinutes -and -not $Once) {
                    continue
                }
            } elseif ($observed[$key].Signature -ne $sig) {
                $observed[$key].Signature = $sig
                $observed[$key].StableSince = $now
                continue
            }

            $stableFor = ($now - [datetime]$observed[$key].StableSince).TotalSeconds
            if (-not $Once -and $stableFor -lt $StableSeconds) { continue }

            $hash = Get-Hash $f.FullName
            if ($published.ContainsKey($hash)) { continue }

            $prefix = Get-RunPrefix $f.Name
            $dir = $f.DirectoryName
            $statsPath = Join-Path $dir ($prefix + '_STATS.csv')
            $tradesPath = Join-Path $dir ($prefix + '_TRADES.csv')

            if (Test-Path -LiteralPath $statsPath) {
                if (-not (Test-StatsFinal $statsPath) -and -not $Once) { continue }
                $group = @()
                foreach ($p in @($statsPath,$tradesPath)) {
                    if (Test-Path -LiteralPath $p) { $group += Get-Item -LiteralPath $p }
                }
                [void](Publish-Group -Files $group -Reason ($(if (Test-StatsFinal $statsPath) {'STATS_FINAL'} else {'MANUAL_ONCE'})) -Published $published)
                continue
            }

            # Generic fallback for CSVs without a STATS companion. It publishes a stable snapshot.
            [void](Publish-Group -Files @($f) -Reason ($(if ($Once) {'MANUAL_ONCE'} else {'STABLE_SNAPSHOT'})) -Published $published)
        }

        if ($Once) { break }
        Start-Sleep -Seconds ([Math]::Max(2,$PollSeconds))
    }
} catch {
    Write-Log "FATAL | $($_.Exception.Message)"
    throw
} finally {
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    try { $mutex.ReleaseMutex() } catch {}
    $mutex.Dispose()
    Write-Log "$TaskLabel STOP"
}
