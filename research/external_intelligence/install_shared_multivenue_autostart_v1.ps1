param(
    [switch]$Remove,
    [switch]$Status,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$TaskName = "Guardian Shared Intelligence MultiVenue V1"
$Runner = Join-Path $PSScriptRoot "run_shared_multivenue_autostart_v1.ps1"
$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$RuntimeScript = Join-Path $PSScriptRoot "shared_runtime_multivenue_bridge_v1.py"

function Show-Status {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        Write-Host "[Guardian] Autostart task: NOT INSTALLED"
        return 1
    }
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "[Guardian] Autostart task: INSTALLED"
    Write-Host ("State      : {0}" -f $task.State)
    Write-Host ("Last run   : {0}" -f $info.LastRunTime)
    Write-Host ("Last result: {0}" -f $info.LastTaskResult)
    Write-Host ("Next run   : {0}" -f $info.NextRunTime)
    return 0
}

if ($Status) {
    exit (Show-Status)
}

if ($Remove) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $task) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[Guardian] Autostart removed."
    }
    else {
        Write-Host "[Guardian] Autostart was not installed."
    }
    exit 0
}

foreach ($required in @($Runner, $PythonExe, $RuntimeScript)) {
    if (-not (Test-Path $required)) {
        throw "Required file missing: $required"
    }
}

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$quotedRunner = '"' + $Runner + '"'
$arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $quotedRunner"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId -RandomDelay (New-TimeSpan -Seconds 30)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Guardian read-only Bybit+Binance Shared Intelligence. Starts 0-30s after Windows logon; one instance only."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
Write-Host "[Guardian] Autostart installed. It will start automatically after Windows logon."

$existingRuntime = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessId -ne $PID -and $_.CommandLine -like "*shared_runtime_multivenue_bridge_v1.py*"
} | Select-Object -First 1

if (-not $NoStart) {
    if ($null -ne $existingRuntime) {
        Write-Host ("[Guardian] Existing manual runtime detected (PID={0})." -f $existingRuntime.ProcessId)
        Write-Host "[Guardian] To avoid duplicate collectors, the scheduled task is installed but is NOT started now."
        Write-Host "[Guardian] It will take over automatically at the next Windows logon."
    }
    else {
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
    }
}

exit (Show-Status)
