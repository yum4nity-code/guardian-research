param(
    [string]$DataDir = "D:\MT5_Backtests\Research\ExternalIntelligence"
)

$ErrorActionPreference = "Stop"
$MutexName = "GuardianSharedMultiVenueRuntimeV1"
$BaseDir = $PSScriptRoot
$PythonExe = Join-Path $BaseDir ".venv\Scripts\python.exe"
$RuntimeScript = Join-Path $BaseDir "shared_runtime_multivenue_bridge_v1.py"
$LogDir = Join-Path $DataDir "logs"
$LogFile = Join-Path $LogDir "shared_multivenue_autostart_v1.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-GuardianLog([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

if (-not (Test-Path $PythonExe)) {
    Write-GuardianLog "[AUTOSTART][FATAL] Missing Python venv: $PythonExe"
    exit 2
}
if (-not (Test-Path $RuntimeScript)) {
    Write-GuardianLog "[AUTOSTART][FATAL] Missing runtime: $RuntimeScript"
    exit 2
}

$mutex = New-Object System.Threading.Mutex($false, $MutexName)
$ownsMutex = $false

try {
    try {
        $ownsMutex = $mutex.WaitOne(0, $false)
    }
    catch [System.Threading.AbandonedMutexException] {
        $ownsMutex = $true
        Write-GuardianLog "[AUTOSTART][RECOVERY] Recovered abandoned runtime mutex."
    }

    if (-not $ownsMutex) {
        Write-GuardianLog "[AUTOSTART][SKIP] Another shared multi-venue runtime wrapper is already active."
        exit 0
    }

    Write-GuardianLog "[AUTOSTART][START] Guardian Shared Intelligence Bybit+Binance supervisor active."

    while ($true) {
        $started = Get-Date
        Write-GuardianLog "[AUTOSTART][LAUNCH] Starting shared_runtime_multivenue_bridge_v1.py"

        try {
            & $PythonExe $RuntimeScript --data-dir $DataDir 2>&1 | ForEach-Object {
                $text = $_.ToString()
                Add-Content -Path $LogFile -Value $text -Encoding UTF8
            }
            $rc = $LASTEXITCODE
        }
        catch {
            $rc = 99
            Write-GuardianLog ("[AUTOSTART][EXCEPTION] " + $_.Exception.Message)
        }

        $elapsed = ((Get-Date) - $started).TotalSeconds
        Write-GuardianLog ("[AUTOSTART][STOP] Runtime exited code={0} after {1:N1}s." -f $rc, $elapsed)

        # Scheduled Task termination stops this wrapper. Any natural runtime exit is treated
        # as abnormal for a persistent service and is restarted with bounded backoff.
        $delay = if ($elapsed -lt 30) { 60 } else { 10 }
        Write-GuardianLog "[AUTOSTART][RESTART] Restarting in ${delay}s unless the task is stopped."
        Start-Sleep -Seconds $delay
    }
}
finally {
    if ($ownsMutex) {
        try { $mutex.ReleaseMutex() } catch { }
    }
    $mutex.Dispose()
}
