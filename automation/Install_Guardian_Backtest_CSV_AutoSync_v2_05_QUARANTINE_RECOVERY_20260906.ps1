param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$RepoRoot='D:\MT5_Backtests\guardian-research'
$Source='D:\MT5_Backtests\automation\Guardian_Backtest_CSV_AutoSync_v2_04_GENERIC_FASTSKIP_RECOVERY_PUBLICSAFE.ps1'
$InstallDir='D:\MT5_Backtests\automation'
$Target=Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE.ps1'
$StartupDir=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd=Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync_v2_05.cmd'
$OldState='D:\MT5_Backtests\guardian-backtest-csv-sync-v204-state.json'
$NewState='D:\MT5_Backtests\guardian-backtest-csv-sync-v205-state.json'
$CommonFiles=Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'

if(-not(Test-Path -LiteralPath $Source)){throw "Installed v2.04 runtime introuvable: $Source"}
New-Item -ItemType Directory -Force -Path $InstallDir,$StartupDir | Out-Null

# Stop only Guardian AutoSync watchers; never touch MT5 or unrelated PowerShell.
$me=$PID
$watchers=Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessId -ne $me -and $_.CommandLine -match 'Guardian_Backtest_CSV_AutoSync|Guardian_D023_CSV_AutoSync' }
foreach($p in $watchers){
    Write-Host "STOP OLD WATCHER pid=$($p.ProcessId) | $($p.CommandLine)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

Get-ChildItem -LiteralPath $StartupDir -Filter 'Guardian*AutoSync*.cmd' -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem 'D:\MT5_Backtests' -Filter 'guardian-*-csv-sync-v*.pid' -File -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

$raw=Get-Content -LiteralPath $Source -Raw

# Version isolation. Keep v2.04 file untouched.
$raw=$raw.Replace('v2.04','v2.05')
$raw=$raw.Replace('v2_04','v2_05')
$raw=$raw.Replace('v204','v205')
$raw=$raw.Replace('V204','V205')
$raw=$raw.Replace('FASTSKIP RECOVERY','QUARANTINE RECOVERY')
$raw=$raw.Replace('GENERIC_FASTSKIP_RECOVERY_PUBLICSAFE','GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE')

# Known-invalid superseded ledgers: v1.00 EURUSD/GBPUSD DEV each have opened=476, closed=475, rows=475.
# They must never be published and must not consume the 20s stability delay forever.
$oldFilter="Where-Object { `$_.Name -match '^D\\d{3}_V.+_STATS\\.csv$' -and `$_.Name -notmatch '^D023_' } |"
$newFilter="Where-Object { `$_.Name -match '^D\\d{3}_V.+_STATS\\.csv$' -and `$_.Name -notmatch '^D023_' -and `$_.Name -notmatch '^D036_V100_DEV_2024_2025_(EURUSD|GBPUSD)_STATS\\.csv$' } |"
if(-not $raw.Contains($oldFilter)){throw 'Expected stats-file filter not found in v2.04 runtime.'}
$raw=$raw.Replace($oldFilter,$newFilter)

# Static assertions before writing or launching.
foreach($needle in @(
    'v2.05',
    'guardian-backtest-csv-sync-v205',
    'D036_V100_DEV_2024_2025_(EURUSD|GBPUSD)',
    'GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE'
)){
    if(-not $raw.Contains($needle)){throw "Generated v2.05 missing assertion: $needle"}
}
if($raw.Contains('guardian-backtest-csv-sync-v204.pid')){throw 'v2.04 PID residue remains in generated runtime.'}

Set-Content -LiteralPath $Target -Value $raw -Encoding UTF8

# Preserve already-published fingerprints so no historical run is duplicated.
if((Test-Path -LiteralPath $OldState) -and -not(Test-Path -LiteralPath $NewState)){
    Copy-Item -LiteralPath $OldState -Destination $NewState
    Write-Host "MIGRATE STATE: $OldState -> $NewState"
}

$cmd='@echo off'+"`r`n"+'start "Guardian Backtest CSV Sync v2.05" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$Target+'"'+"`r`n"
Set-Content -LiteralPath $StartupCmd -Value $cmd -Encoding ASCII
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$Target`"")

Start-Sleep -Seconds 2
$active=Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match [regex]::Escape('Guardian_Backtest_CSV_AutoSync_v2_05_GENERIC_QUARANTINE_RECOVERY_PUBLICSAFE.ps1') }

Write-Host "INSTALLE: $Target"
Write-Host "AUTOSTART: $StartupCmd"
Write-Host "ACTIVE V2.05 WATCHERS: $(@($active).Count)"
foreach($p in $active){Write-Host "ACTIVE pid=$($p.ProcessId) | $($p.CommandLine)"}

Write-Host "`n=== LOCAL V101 D036 DEV FILES ==="
$v101=@(Get-ChildItem -LiteralPath $CommonFiles -File -Filter 'D036_V101_DEV_2024_2025_*_STATS.csv' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
if($v101.Count -eq 0){
    Write-Host 'V101 STATS COUNT: 0'
}else{
    Write-Host "V101 STATS COUNT: $($v101.Count)"
    foreach($f in $v101){
        Write-Host "--- $($f.Name) ---"
        Get-Content -LiteralPath $f.FullName -Tail 1
    }
}

# Allow the persistent watcher enough time to publish up to two new stable V101 pairs.
Start-Sleep -Seconds 50

Write-Host "`n=== V2.05 HEALTH ==="
$health='D:\MT5_Backtests\guardian-backtest-csv-sync-v205-health.json'
if(Test-Path -LiteralPath $health){Get-Content -LiteralPath $health}else{Write-Host 'health file not created'}
Write-Host "`n=== V2.05 LOG TAIL ==="
$log='D:\MT5_Backtests\logs\guardian-backtest-csv-sync-v205.log'
if(Test-Path -LiteralPath $log){Get-Content -LiteralPath $log -Tail 20}else{Write-Host 'log file not created'}
