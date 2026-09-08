$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$TaskName = 'GuardianResearchOrchestratorV1'
$Root = 'D:\MT5_Backtests\Research\Autonomous'
$RuntimeDir = Join-Path $Root 'runtime'
$RuntimeScript = Join-Path $RuntimeDir 'guardian_research_orchestrator_v1_00.py'
$Deploy = 'D:\MT5_Backtests\guardian-autonomous-main'
$Remote = 'https://github.com/yum4nity-code/guardian-research.git'
$Marker = Join-Path $Root 'hidden_task_repair.json'

if (-not (Test-Path -LiteralPath $RuntimeScript)) { throw "Runtime script missing: $RuntimeScript" }
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop

$pythonExe = (& py.exe -3 -c "import sys; print(sys.executable)").Trim()
if (-not $pythonExe -or -not (Test-Path -LiteralPath $pythonExe)) { throw 'Could not resolve Python executable via py -3.' }
$pythonw = Join-Path (Split-Path -Parent $pythonExe) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw "pythonw.exe missing beside interpreter: $pythonw" }

$arguments = '"' + $RuntimeScript + '" --root "' + $Root + '" --deploy "' + $Deploy + '" --remote "' + $Remote + '" --poll-seconds 60'
$action = New-ScheduledTaskAction -Execute $pythonw -Argument $arguments -WorkingDirectory $RuntimeDir
Set-ScheduledTask -TaskName $TaskName -Action $action | Out-Null

$verify = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$actual = [string]$verify.Actions[0].Execute
if (-not [string]::Equals($actual,$pythonw,[System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Scheduled Task action verification failed. Expected $pythonw, got $actual"
}

$payload = [ordered]@{
    schema = 1
    status = 'PASS'
    repaired_at_utc = [DateTime]::UtcNow.ToString('o')
    task = $TaskName
    execute = $actual
    runtime = $RuntimeScript
    current_console_hide_attempted = $false
}

# The repair job is launched as a child of the currently visible orchestrator console.
# Hide that shared console now; future task starts use pythonw.exe and create no console.
try {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class GuardianConsole {
    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@ -ErrorAction Stop
    $hwnd = [GuardianConsole]::GetConsoleWindow()
    if ($hwnd -ne [IntPtr]::Zero) {
        [void][GuardianConsole]::ShowWindow($hwnd,0)
        $payload.current_console_hide_attempted = $true
    }
} catch {
    $payload.current_console_hide_error = $_.Exception.Message
}

$payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Marker -Encoding UTF8
Write-Host 'ORCHESTRATOR_HIDDEN_REPAIR_PASS'
