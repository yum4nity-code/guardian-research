param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$CommonFiles = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$ResultsRepo = 'D:\MT5_Backtests\guardian-backtest-autosync-results'
$Branch = 'backtest-results'
$WatcherRuntime = 'D:\MT5_Backtests\automation\Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE.ps1'
$Symbols = @('BTCUSD','ETHUSD','EURUSD','GBPUSD','USDJPY','XAUUSD')

function Run-Git {
    param([string[]]$GitArgs)
    $output = & git @GitArgs 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ('git failed: ' + ($GitArgs -join ' ') + "`n" + ($output -join "`n"))
    }
    return @($output)
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

Write-Host '=== D037 RAW RECOVERY DUMP v1.00 ==='

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

$watchers = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE\.ps1' })

$stoppedWatcher = $false
foreach ($proc in $watchers) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    $stoppedWatcher = $true
    Write-Host ('PAUSED AUTOSYNC PID {0}' -f $proc.ProcessId)
}

try {
    Push-Location $ResultsRepo
    try {
        Run-Git @('fetch','origin',$Branch) | Out-Null
        Run-Git @('checkout',$Branch) | Out-Null
        Run-Git @('pull','--ff-only','origin',$Branch) | Out-Null

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
            schema = 1
            reason = 'D037_RAW_RECOVERY_DUMP_NO_FINAL_REQUIRED'
            created_at = (Get-Date).ToString('o')
            file_count = $found.Count
            symbols = @($found | Select-Object -ExpandProperty Symbol -Unique)
            note = 'Raw local dump for remote audit. Presence here does not imply validation.'
        }
        $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $dest 'recovery_manifest.json') -Encoding UTF8

        Run-Git @('add','--',$destRel) | Out-Null
        $status = @(& git status --porcelain -- $destRel)
        if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
        if ($status.Count -eq 0) { throw 'Nothing staged for D037 raw dump.' }

        Run-Git @('commit','-m',('Raw recovery dump D037 ' + $stamp)) | Out-Null

        $push = & git push origin $Branch 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'Push raced another writer; retrying once with rebase.'
            Run-Git @('pull','--rebase','origin',$Branch) | Out-Null
            Run-Git @('push','origin',$Branch) | Out-Null
        }

        $head = (Run-Git @('rev-parse','HEAD'))[0]
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
            Where-Object { $_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE\.ps1' })
        if ($active.Count -eq 0) {
            Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + $WatcherRuntime + '"'))
            Start-Sleep -Seconds 2
            Write-Host 'AUTOSYNC RESTARTED'
        }
    }
}

Write-Host 'DONE'
