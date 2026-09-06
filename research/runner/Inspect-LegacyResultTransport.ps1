$ErrorActionPreference = 'Stop'

Write-Host '=== Guardian legacy result transport inspection (READ ONLY) ==='
Write-Host 'This script does not stop, disable, unregister, delete, or edit anything.'
Write-Host ''

$pattern = '(?i)(guardian|autosync|auto-sync|backtest|live_status|live-status|result_transport)'

Write-Host '--- Scheduled tasks with matching name/path/action ---'
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
    $task = $_
    $actionText = (($task.Actions | ForEach-Object { "Execute=$($_.Execute) Arguments=$($_.Arguments)" }) -join ' | ')
    $haystack = "$($task.TaskPath)$($task.TaskName) $actionText"
    if ($haystack -match $pattern) {
        $info = Get-ScheduledTaskInfo -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction SilentlyContinue
        [PSCustomObject]@{
            TaskPath       = $task.TaskPath
            TaskName       = $task.TaskName
            State          = $task.State
            LastRunTime    = if ($info) { $info.LastRunTime } else { $null }
            LastTaskResult = if ($info) { $info.LastTaskResult } else { $null }
            Actions        = $actionText
        }
    }
}

if ($tasks) {
    $tasks | Sort-Object TaskPath, TaskName | Format-List
} else {
    Write-Host 'No matching scheduled tasks found.'
}

Write-Host ''
Write-Host '--- Running processes with matching command line ---'
$processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and $_.CommandLine -match $pattern
} | Select-Object ProcessId, Name, ExecutablePath, CommandLine

if ($processes) {
    $processes | Sort-Object ProcessId | Format-List
} else {
    Write-Host 'No matching running process command lines found.'
}

Write-Host ''
Write-Host '--- Guidance ---'
Write-Host 'Look specifically for the process/task responsible for Git commits authored as:'
Write-Host '  Guardian Backtest Bot <guardian-backtest@local>'
Write-Host 'with commit messages beginning:'
Write-Host '  Auto-sync validated ...'
Write-Host ''
Write-Host 'Do NOT disable a task merely because it contains the word Guardian.'
Write-Host 'The deterministic research runner/result_transport.py is not a daemon and does not need a scheduled task.'
