param()

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$RepoRoot='D:\MT5_Backtests\guardian-research'
$WatcherScript=Join-Path $RepoRoot 'automation\Guardian_Backtest_CSV_AutoSync_v2_02_GENERIC_LOCALMUTEX_RECOVERY_PUBLICSAFE.ps1'
$StartupDir=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'

Write-Host '=== Guardian AutoSync CLEAN RESET ==='

# Stop every prior/current Guardian CSV AutoSync PowerShell process by command line.
$watchers=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -match '^(powershell|pwsh)\.exe$') -and
    $_.CommandLine -and
    ($_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync_|Guardian_D023_CSV_AutoSync_') -and
    ([int]$_.ProcessId -ne $PID)
})

foreach($p in $watchers){
    Write-Host ("STOP pid={0} | {1}" -f $p.ProcessId,$p.CommandLine)
    Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# Remove every historical Guardian CSV AutoSync startup launcher.
if(Test-Path -LiteralPath $StartupDir){
    Get-ChildItem -LiteralPath $StartupDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^Guardian_.*CSV_AutoSync.*\.cmd$' } |
        ForEach-Object { Write-Host ("REMOVE AUTOSTART: {0}" -f $_.FullName); Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }
}

# Remove stale PID markers only. State files/logs/results are intentionally preserved.
Get-ChildItem -LiteralPath 'D:\MT5_Backtests' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^guardian-.*csv-sync-v\d+\.pid$' } |
    ForEach-Object { Write-Host ("REMOVE PID: {0}" -f $_.FullName); Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }

if(-not (Test-Path -LiteralPath $WatcherScript)){
    throw "Watcher v2.02 absent: $WatcherScript"
}

# Install/start exactly one watcher. v2.02 itself recreates the single startup launcher.
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $WatcherScript -Install
Start-Sleep -Seconds 3

$after=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -match '^(powershell|pwsh)\.exe$') -and
    $_.CommandLine -and
    ($_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync_v2_02_GENERIC_LOCALMUTEX_RECOVERY_PUBLICSAFE\.ps1')
})

Write-Host ("ACTIVE V2.02 WATCHERS: {0}" -f $after.Count)
foreach($p in $after){ Write-Host ("ACTIVE pid={0} | {1}" -f $p.ProcessId,$p.CommandLine) }

if($after.Count -ne 1){
    throw "Expected exactly 1 active v2.02 watcher, found $($after.Count)."
}

$Health='D:\MT5_Backtests\guardian-backtest-csv-sync-v202-health.json'
$Log='D:\MT5_Backtests\logs\guardian-backtest-csv-sync-v202.log'
if(Test-Path -LiteralPath $Health){ Write-Host '--- HEALTH ---'; Get-Content -LiteralPath $Health }
if(Test-Path -LiteralPath $Log){ Write-Host '--- LOG TAIL ---'; Get-Content -LiteralPath $Log -Tail 15 }
