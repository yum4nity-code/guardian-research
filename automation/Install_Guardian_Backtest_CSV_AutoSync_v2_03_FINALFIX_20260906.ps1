param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$RepoRoot='D:\MT5_Backtests\guardian-research'
$Source=Join-Path $RepoRoot 'automation\Guardian_Backtest_CSV_AutoSync_v2_02_GENERIC_LOCALMUTEX_RECOVERY_PUBLICSAFE.ps1'
$InstallDir='D:\MT5_Backtests\automation'
$Target=Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v2_03_GENERIC_FINALFIX_PUBLICSAFE.ps1'
$StartupDir=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$TargetStartup=Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync_v2_03.cmd'

if(-not(Test-Path -LiteralPath $Source)){throw "Source v2.02 introuvable: $Source"}
New-Item -ItemType Directory -Force -Path $InstallDir,$StartupDir|Out-Null

# Stop only Guardian AutoSync PowerShell processes, never arbitrary PowerShell sessions.
$me=$PID
$procs=Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessId -ne $me -and $_.CommandLine -match 'Guardian_.*AutoSync|guardian-backtest-csv-sync|guardian-d023-csv-sync' }
foreach($p in $procs){
    Write-Host "STOP OLD WATCHER pid=$($p.ProcessId) | $($p.CommandLine)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

Get-ChildItem -LiteralPath $StartupDir -Filter 'Guardian*AutoSync*.cmd' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath $StartupDir -Filter 'Guardian_D023_CSV_AutoSync*.cmd' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem 'D:\MT5_Backtests' -Filter 'guardian-*-csv-sync-v*.pid' -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

$raw=Get-Content -LiteralPath $Source -Raw

# Version/path isolation: do not overwrite v2.02.
$raw=$raw.Replace('v2.02','v2.03')
$raw=$raw.Replace('v2_02','v2_03')
$raw=$raw.Replace('v202','v203')
$raw=$raw.Replace('V202','V203')
$raw=$raw.Replace('LOCALMUTEX RECOVERY','FINALFIX')
$raw=$raw.Replace('GENERIC_LOCALMUTEX_RECOVERY_PUBLICSAFE','GENERIC_FINALFIX_PUBLICSAFE')

# Critical bug fix: -notmatch on an ARRAY returns all non-matching lines and is truthy even when FINAL exists.
$bad="if (`$tail -notmatch '(^|;)FINAL(;|`$)') { continue }"
$good="if (-not (`$tail -match '(^|;)FINAL(;|`$)')) { continue }"
if(-not $raw.Contains($bad)){throw 'Expected v2.02 FINAL-detection line not found; refusing unsafe patch.'}
$raw=$raw.Replace($bad,$good)

# Ensure the state file exists immediately for observability, even before first publication.
$anchor="Set-Content -LiteralPath `$PidFile -Value `$PID -Encoding ASCII"
$replacement=$anchor+"`r`n`$initialState=Load-State`r`nSave-State `$initialState"
if(-not $raw.Contains($anchor)){throw 'PID anchor not found; refusing unsafe patch.'}
$raw=$raw.Replace($anchor,$replacement)

Set-Content -LiteralPath $Target -Value $raw -Encoding UTF8

# Verify the critical condition in the generated watcher before launch.
$check=Get-Content -LiteralPath $Target -Raw
if($check -notmatch [regex]::Escape($good)){throw 'Generated v2.03 does not contain corrected FINAL condition.'}

$cmd='@echo off'+"`r`n"+'start "Guardian Backtest CSV Sync v2.03" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$Target+'"'+"`r`n"
Set-Content -LiteralPath $TargetStartup -Value $cmd -Encoding ASCII
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$Target`"")

Start-Sleep -Seconds 2
$active=Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match [regex]::Escape('Guardian_Backtest_CSV_AutoSync_v2_03_GENERIC_FINALFIX_PUBLICSAFE.ps1') }
Write-Host "INSTALLE: $Target"
Write-Host "AUTOSTART: $TargetStartup"
Write-Host "ACTIVE V2.03 WATCHERS: $(@($active).Count)"
foreach($p in $active){Write-Host "ACTIVE pid=$($p.ProcessId) | $($p.CommandLine)"}
Write-Host 'HEALTH: D:\MT5_Backtests\guardian-backtest-csv-sync-v203-health.json'
Write-Host 'STATE:  D:\MT5_Backtests\guardian-backtest-csv-sync-v203-state.json'
Write-Host 'LOG:    D:\MT5_Backtests\logs\guardian-backtest-csv-sync-v203.log'
