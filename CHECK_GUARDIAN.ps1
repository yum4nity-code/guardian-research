$ErrorActionPreference = 'Stop'
$path = 'D:\MT5_Backtests\Research\Autonomous\orchestrator_health.json'

Write-Host ''

if (-not (Test-Path -LiteralPath $path)) {
    Write-Host '[ROUGE] STOPPE / INJOIGNABLE' -ForegroundColor Red
    Write-Host 'Aucun fichier de heartbeat trouve.'
    exit 0
}

try {
    $raw = [System.IO.File]::ReadAllText($path)
    $h = $raw | ConvertFrom-Json
} catch {
    Write-Host '[ROUGE] HEARTBEAT ILLISIBLE' -ForegroundColor Red
    Write-Host ('Erreur: ' + $_.Exception.Message)
    Write-Host ('Fichier: ' + $path)
    exit 0
}

try {
    $t = [DateTimeOffset]::Parse([string]$h.updated_at_utc)
    $age = ((Get-Date).ToUniversalTime() - $t.UtcDateTime).TotalSeconds
} catch {
    Write-Host '[ROUGE] DATE DE HEARTBEAT INVALIDE' -ForegroundColor Red
    Write-Host ('updated_at_utc = ' + [string]$h.updated_at_utc)
    exit 0
}

$job = ''
if ($null -ne $h.active_job) {
    $job = [string]$h.active_job.id + ' r' + [string]$h.active_job.revision
} elseif ($h.last_receipt) {
    $job = Split-Path ([string]$h.last_receipt) -Leaf
}

$status = [string]$h.status
if ($status -eq 'RUNNING' -and $age -lt 180) {
    Write-Host '[VERT] CA BOSSE' -ForegroundColor Green
} elseif (($status -in @('WAITING','IDLE','PASS')) -and $age -lt 180) {
    Write-Host '[ORANGE] EN ATTENTE / ENTRE DEUX JOBS' -ForegroundColor Yellow
} elseif ($status -in @('FAIL','TIMEOUT','BLOCKED','ORCHESTRATOR_ERROR')) {
    Write-Host '[ROUGE] BLOQUE / ERREUR' -ForegroundColor Red
} elseif ($age -ge 180) {
    Write-Host '[ROUGE] STOPPE ? HEARTBEAT TROP VIEUX' -ForegroundColor Red
} else {
    Write-Host '[ORANGE] ETAT A VERIFIER' -ForegroundColor Yellow
}

Write-Host ('Etat brut      : ' + $status)
Write-Host ('Dernier signal : ' + $t.ToLocalTime().ToString('dd/MM/yyyy HH:mm:ss'))
Write-Host ('Age            : ' + [math]::Round($age) + ' s')
if ($job) { Write-Host ('Job            : ' + $job) }
Write-Host ''
