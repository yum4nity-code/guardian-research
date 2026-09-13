param(
    [string]$Root = 'D:\MT5_Backtests',
    [int]$RefreshSeconds = 5
)

$ErrorActionPreference = 'SilentlyContinue'
$progressDir = Join-Path $Root 'Research\Autonomous\progress'
$reportsDir  = Join-Path $Root 'Research\Autonomous\reports'
$logsDir     = Join-Path $Root 'Research\Autonomous\logs'

function Get-LatestFile([string]$Path,[string]$Filter='*') {
    if (!(Test-Path -LiteralPath $Path)) { return $null }
    Get-ChildItem -LiteralPath $Path -File -Filter $Filter |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Shorten([string]$s,[int]$n=140) {
    if ([string]::IsNullOrWhiteSpace($s)) { return '' }
    $x = ($s -replace '\s+',' ').Trim()
    if ($x.Length -le $n) { return $x }
    return $x.Substring(0,$n-3) + '...'
}

while ($true) {
    Clear-Host
    $now = Get-Date
    Write-Host ('GUARDIAN RESEARCH WATCH   ' + $now.ToString('yyyy-MM-dd HH:mm:ss'))
    Write-Host ('=' * 78)

    $procs = Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match 'research|guardian|r1[0-9]_|autonomous' -and $_.Name -match 'python|powershell|pwsh' }

    Write-Host ''
    Write-Host 'PROCESSUS ACTIFS'
    if ($procs) {
        foreach ($p in $procs) {
            $gp = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
            $cpu = if ($gp) { [math]::Round($gp.CPU,1) } else { $null }
            $rss = if ($gp) { [math]::Round($gp.WorkingSet64/1MB,1) } else { $null }
            Write-Host ("PID {0,-7} CPU {1,8}s  RAM {2,8} MB  {3}" -f $p.ProcessId,$cpu,$rss,(Shorten $p.CommandLine 170))
        }
    } else {
        Write-Host 'Aucun moteur de recherche detecte.'
    }

    Write-Host ''
    Write-Host 'DERNIER PROGRESS JSON'
    $pf = Get-LatestFile $progressDir '*.json'
    if ($pf) {
        Write-Host ("{0}   modifie {1}" -f $pf.Name,$pf.LastWriteTime.ToString('HH:mm:ss'))
        try {
            $j = Get-Content -LiteralPath $pf.FullName -Raw | ConvertFrom-Json
            foreach ($k in @('stage','status','family','candidate','symbol','completed','total','tested','discovery_candidates','confirmation_candidates','pre_oos_survivors','message')) {
                if ($null -ne $j.$k) { Write-Host ("  {0,-24}: {1}" -f $k,(Shorten ([string]$j.$k) 160)) }
            }
            if ($null -ne $j.completed -and $null -ne $j.total -and [double]$j.total -gt 0) {
                $pct = [math]::Round(100.0 * [double]$j.completed / [double]$j.total,2)
                Write-Host ("  avancement              : {0}%" -f $pct)
            }
        } catch {
            Write-Host '  JSON illisible; affichage brut:'
            Get-Content -LiteralPath $pf.FullName -Tail 12
        }
    } else {
        Write-Host "Aucun fichier JSON trouve dans $progressDir"
    }

    Write-Host ''
    Write-Host 'DERNIERS FICHIERS DE PROGRESSION'
    if (Test-Path -LiteralPath $progressDir) {
        Get-ChildItem -LiteralPath $progressDir -File |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 6 Name,LastWriteTime,Length |
            Format-Table -AutoSize
    }

    Write-Host 'DERNIER LOG'
    $lf = Get-LatestFile $logsDir '*.log'
    if ($lf) {
        Write-Host ("{0}   modifie {1}" -f $lf.Name,$lf.LastWriteTime.ToString('HH:mm:ss'))
        Get-Content -LiteralPath $lf.FullName -Tail 12
    } else {
        Write-Host "Aucun .log trouve dans $logsDir"
    }

    Write-Host ''
    Write-Host 'DERNIER RAPPORT'
    $rf = Get-LatestFile $reportsDir '*'
    if ($rf) {
        Write-Host ("{0}   modifie {1}   {2:N1} KB" -f $rf.Name,$rf.LastWriteTime.ToString('HH:mm:ss'),($rf.Length/1KB))
    } else {
        Write-Host "Aucun rapport trouve dans $reportsDir"
    }

    Write-Host ''
    Write-Host ('Rafraichissement toutes les {0}s - Ctrl+C pour quitter' -f $RefreshSeconds)
    Start-Sleep -Seconds $RefreshSeconds
}
