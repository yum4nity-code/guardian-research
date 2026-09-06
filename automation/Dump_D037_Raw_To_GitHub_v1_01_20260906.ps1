param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$CommonFiles = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$ResultsRepo = 'D:\MT5_Backtests\guardian-backtest-autosync-results'
$Branch = 'backtest-results'
$WatcherRuntime = 'D:\MT5_Backtests\automation\Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE.ps1'
$Symbols = @('BTCUSD','ETHUSD','EURUSD','GBPUSD','USDJPY','XAUUSD')

function Invoke-GitSafe {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$GitArgs,
        [switch]$Quiet
    )

    $stderrFile = Join-Path $env:TEMP ('guardian_git_stderr_' + [guid]::NewGuid().ToString('N') + '.txt')
    $oldPreference = $ErrorActionPreference
    try {
        # Native git writes normal progress (for example "From https://...") to stderr.
        # Never merge stderr into PowerShell's error stream. The exit code is authoritative.
        $ErrorActionPreference = 'Continue'
        $stdout = @(& git @GitArgs 2> $stderrFile)
        $exitCode = $LASTEXITCODE
        $stderr = @()
        if (Test-Path -LiteralPath $stderrFile) {
            $stderr = @(Get-Content -LiteralPath $stderrFile -ErrorAction SilentlyContinue)
        }
    }
    finally {
        $ErrorActionPreference = $oldPreference
        Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
    }

    if (-not $Quiet) {
        foreach ($line in $stdout) { if ($null -ne $line -and "$line" -ne '') { Write-Host $line } }
        foreach ($line in $stderr) { if ($null -ne $line -and "$line" -ne '') { Write-Host $line } }
    }

    if ($exitCode -ne 0) {
        $details = (@($stdout) + @($stderr)) -join "`n"
        throw ('git ' + ($GitArgs -join ' ') + ' failed with exit code ' + $exitCode + "`n" + $details)
    }

    return @($stdout)
}

function Copy-SanitizedStats {
    param([string]$Source,[string]$Destination)

    $raw = Get-Content -LiteralPath $Source -Raw
    if ($env:USERPROFILE) {
        $raw = $raw.Replace($env:USERPROFILE,'C:\Users\<REDACTED>')
    }
    if ($env:USERNAME) {
        $raw = $raw.Replace(('C:\Users\' + $env:USERNAME),'C:\Users\<REDACTED>')
    }
    Set-Content -LiteralPath $Destination -Value $raw -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $CommonFiles)) {
    throw ('MT5 FILE_COMMON missing: ' + $CommonFiles)
}
if (-not (Test-Path -LiteralPath (Join-Path $ResultsRepo '.git'))) {
    throw ('Results clone missing: ' + $ResultsRepo)
}

Write-Host '=== D037 RAW RECOVERY DUMP v1.01 ==='
Write-Host 'Collecting local files...'

$found = @()
foreach ($symbol in $Symbols) {
    $stats = Join-Path $CommonFiles ('D037_V100_DEV_2024_2025_' + $symbol + '_STATS.csv')
    $trades = Join-Path $CommonFiles ('D037_V100_DEV_2024_2025_' + $symbol + '_TRADES.csv')

    if (Test-Path -LiteralPath $stats) {
        $found += [pscustomobject]@{ Symbol=$symbol; Kind='STATS'; Path=$stats }
        Write-Host ('FOUND {0} STATS' -f $symbol)
    } else {
        Write-Host ('MISSING {0} STATS' -f $symbol)
    }

    if (Test-Path -LiteralPath $trades) {
        $found += [pscustomobject]@{ Symbol=$symbol; Kind='TRADES'; Path=$trades }
        Write-Host ('FOUND {0} TRADES' -f $symbol)
    } else {
        Write-Host ('MISSING {0} TRADES' -f $symbol)
    }
}

if ($found.Count -eq 0) {
    throw 'No D037 files found.'
}

Write-Host ('FILES FOUND: {0}' -f $found.Count)

$watchers = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ProcessId -ne $PID -and
        $_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE\.ps1'
    })

$stoppedWatcher = $false
foreach ($proc in $watchers) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    $stoppedWatcher = $true
    Write-Host ('PAUSED AUTOSYNC PID {0}' -f $proc.ProcessId)
}

try {
    Push-Location $ResultsRepo
    try {
        $dirty = @(& git status --porcelain 2>$null)
        if ($LASTEXITCODE -ne 0) { throw 'git status failed in results clone' }
        if ($dirty.Count -gt 0) {
            throw ("Results clone is dirty; refusing to overwrite anything:`n" + ($dirty -join "`n"))
        }

        Write-Host 'SYNC RESULTS BRANCH...'
        Invoke-GitSafe -GitArgs @('fetch','origin',$Branch) -Quiet | Out-Null
        Invoke-GitSafe -GitArgs @('checkout',$Branch) -Quiet | Out-Null
        Invoke-GitSafe -GitArgs @('pull','--ff-only','origin',$Branch) -Quiet | Out-Null

        $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        $datePath = Get-Date -Format 'yyyy/MM/dd'
        $destRel = 'backtests/recovery/' + $datePath + '/' + $stamp + '_D037_RAW_DUMP'
        $dest = Join-Path $ResultsRepo ($destRel -replace '/','\')
        New-Item -ItemType Directory -Force -Path $dest | Out-Null

        foreach ($item in $found) {
            $name = Split-Path -Leaf $item.Path
            $target = Join-Path $dest $name
            if ($item.Kind -eq 'STATS') {
                Copy-SanitizedStats -Source $item.Path -Destination $target
            } else {
                Copy-Item -LiteralPath $item.Path -Destination $target -Force
            }
            Write-Host ('COPIED {0} {1}' -f $item.Symbol,$item.Kind)
        }

        $manifest = [ordered]@{
            schema = 2
            reason = 'D037_RAW_RECOVERY_DUMP_NO_FINAL_REQUIRED'
            created_at = (Get-Date).ToString('o')
            file_count = $found.Count
            symbols = @($found | Select-Object -ExpandProperty Symbol -Unique)
            note = 'Raw local dump for remote audit. Presence here does not imply validation.'
        }
        $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $dest 'recovery_manifest.json') -Encoding UTF8

        Invoke-GitSafe -GitArgs @('add','--',$destRel) -Quiet | Out-Null
        $status = @(& git status --porcelain -- $destRel 2>$null)
        if ($LASTEXITCODE -ne 0) { throw 'git status failed after staging' }
        if ($status.Count -eq 0) { throw 'Nothing staged for D037 raw dump.' }

        Write-Host 'COMMITTING RAW DUMP...'
        Invoke-GitSafe -GitArgs @('commit','-m',('Raw recovery dump D037 ' + $stamp)) -Quiet | Out-Null

        Write-Host 'PUSHING RAW DUMP...'
        try {
            Invoke-GitSafe -GitArgs @('push','origin',$Branch) -Quiet | Out-Null
        }
        catch {
            Write-Host 'Push raced another writer; retrying once with rebase...'
            Invoke-GitSafe -GitArgs @('pull','--rebase','origin',$Branch) -Quiet | Out-Null
            Invoke-GitSafe -GitArgs @('push','origin',$Branch) -Quiet | Out-Null
        }

        $head = (Invoke-GitSafe -GitArgs @('rev-parse','HEAD') -Quiet)[0]
        Write-Host ('PUBLISHED RAW DUMP: ' + $destRel)
        Write-Host ('COMMIT: ' + $head)
    }
    finally {
        Pop-Location
    }
}
finally {
    if (Test-Path -LiteralPath $WatcherRuntime) {
        $active = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE\.ps1'
            })

        if ($active.Count -eq 0) {
            Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
                '-NoProfile',
                '-ExecutionPolicy','Bypass',
                '-File',('"' + $WatcherRuntime + '"')
            )
            Start-Sleep -Seconds 2
            Write-Host 'AUTOSYNC RESTARTED'
        } else {
            Write-Host ('AUTOSYNC ACTIVE: {0} watcher(s)' -f $active.Count)
        }
    }
}

Write-Host 'DONE'
