param(
    [switch]$Remove,
    [switch]$Status,
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
$TaskName = 'Guardian Live Research Status Sync'
$Watcher = Join-Path $PSScriptRoot 'live_status_sync_v2.ps1'

function Show-Status {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        Write-Host '[Guardian] Live-status sync: NOT INSTALLED'
        return 1
    }
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host '[Guardian] Live-status sync: INSTALLED'
    Write-Host ("State      : {0}" -f $task.State)
    Write-Host ("Last run   : {0}" -f $info.LastRunTime)
    Write-Host ("Last result: {0}" -f $info.LastTaskResult)
    return 0
}

if ($Status) { exit (Show-Status) }

if ($Remove) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $task) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    Write-Host '[Guardian] Live-status sync removed.'
    exit 0
}

if (-not (Test-Path $Watcher)) { throw "Missing watcher: $Watcher" }
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { throw 'git.exe not found in PATH.' }

Write-Host '[Guardian] Testing one live-status publication...'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Watcher -Once
if ($LASTEXITCODE -ne 0) { throw 'Initial live-status publication failed.' }

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $Watcher + '"'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId -RandomDelay (New-TimeSpan -Seconds 45)
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
    -Description 'Publishes compact Guardian/D025 live research state to dedicated GitHub live-status branch.'

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
if (-not $NoStart) {
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 2
}
exit (Show-Status)
