$ErrorActionPreference = 'Stop'
$path = 'D:\MT5_Backtests\Research\Autonomous\orchestrator_health.json'
$refreshSeconds = 5

function Show-GuardianStatus {
    Clear-Host
    Write-Host 'GUARDIAN RESEARCH - LIVE' -ForegroundColor Cyan
    Write-Host ('Rafraichissement toutes les ' + $refreshSeconds + ' s - Ctrl+C pour fermer') -ForegroundColor DarkGray
    Write-Host ''

    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host '[ROUGE] STOPPE / INJOIGNABLE' -ForegroundColor Red
        Write-Host 'Aucun fichier de heartbeat trouve.'
        return
    }

    try {
        $raw = [System.IO.File]::ReadAllText($path)
        $h = $raw | ConvertFrom-Json
    } catch {
        Write-Host '[ROUGE] HEARTBEAT ILLISIBLE' -ForegroundColor Red
        Write-Host ('Erreur: ' + $_.Exception.Message)
        Write-Host ('Fichier: ' + $path)
        return
    }

    try {
        $t = [DateTimeOffset]::Parse([string]$h.updated_at_utc)
        $age = ((Get-Date).ToUniversalTime() - $t.UtcDateTime).TotalSeconds
    } catch {
        Write-Host '[ROUGE] DATE DE HEARTBEAT INVALIDE' -ForegroundColor Red
        Write-Host ('updated_at_utc = ' + [string]$h.updated_at_utc)
        return
    }

    $pidAlive = $false
    $guardianPid = 0
    try {
        $guardianPid = [int]$h.pid
        if ($guardianPid -gt 0) {
            $null = Get-Process -Id $guardianPid -ErrorAction Stop
            $pidAlive = $true
        }
    } catch {
        $pidAlive = $false
    }

    $job = ''
    if ($null -ne $h.active_job) {
        $job = [string]$h.active_job.id + ' r' + [string]$h.active_job.revision
    } elseif ($h.last_receipt) {
        $job = Split-Path ([string]$h.last_receipt) -Leaf
    }

    $status = [string]$h.status

    if ($pidAlive -and $status -eq 'RUNNING') {
        Write-Host '[VERT] CA BOSSE' -ForegroundColor Green
    } elseif ($pidAlive -and ($status -in @('WAITING','IDLE','PASS'))) {
        Write-Host '[ORANGE] EN ATTENTE / ENTRE DEUX JOBS' -ForegroundColor Yellow
    } elseif ($pidAlive -and ($status -in @('FAIL','TIMEOUT','BLOCKED','ORCHESTRATOR_ERROR'))) {
        Write-Host '[ROUGE] BLOQUE / ERREUR' -ForegroundColor Red
    } elseif (-not $pidAlive -and $age -ge 90) {
        Write-Host '[ROUGE] STOPPE - ORCHESTRATEUR ABSENT' -ForegroundColor Red
    } elseif (-not $pidAlive) {
        Write-Host '[ORANGE] PROCESSUS ABSENT, VERIFICATION EN COURS' -ForegroundColor Yellow
    } else {
        Write-Host '[ORANGE] ETAT A VERIFIER' -ForegroundColor Yellow
    }

    Write-Host ('Etat brut      : ' + $status)
    Write-Host ('Processus      : ' + $(if ($pidAlive) { 'ACTIF (PID ' + $guardianPid + ')' } else { 'ABSENT' }))
    Write-Host ('Dernier signal : ' + $t.ToLocalTime().ToString('dd/MM/yyyy HH:mm:ss'))
    Write-Host ('Age signal     : ' + [math]::Round($age) + ' s')
    if ($job) { Write-Host ('Job            : ' + $job) }
    Write-Host ''
    Write-Host 'Tu peux laisser cette fenetre ouverte toute la journee.' -ForegroundColor DarkGray
    Write-Host 'Si elle passe en ROUGE, copie-moi simplement ce qui est affiche.' -ForegroundColor DarkGray
}

while ($true) {
    try {
        Show-GuardianStatus
    } catch {
        Clear-Host
        Write-Host '[ROUGE] ERREUR DU CHECKER' -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
    Start-Sleep -Seconds $refreshSeconds
}
