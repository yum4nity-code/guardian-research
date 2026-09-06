param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$RepoRoot='D:\MT5_Backtests\guardian-research'
$Source=Join-Path $RepoRoot 'automation\Guardian_Backtest_CSV_AutoSync_v2_02_GENERIC_LOCALMUTEX_RECOVERY_PUBLICSAFE.ps1'
$InstallDir='D:\MT5_Backtests\automation'
$Target=Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v2_04_GENERIC_FASTSKIP_RECOVERY_PUBLICSAFE.ps1'
$StartupDir=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$TargetStartup=Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync_v2_04.cmd'
$OldState='D:\MT5_Backtests\guardian-backtest-csv-sync-v203-state.json'
$NewState='D:\MT5_Backtests\guardian-backtest-csv-sync-v204-state.json'

if(-not(Test-Path -LiteralPath $Source)){throw "Source v2.02 introuvable: $Source"}
New-Item -ItemType Directory -Force -Path $InstallDir,$StartupDir|Out-Null

# Stop only Guardian AutoSync PowerShell processes.
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

# Version/path isolation.
$raw=$raw.Replace('v2.02','v2.04')
$raw=$raw.Replace('v2_02','v2_04')
$raw=$raw.Replace('v202','v204')
$raw=$raw.Replace('V202','V204')
$raw=$raw.Replace('LOCALMUTEX RECOVERY','FASTSKIP RECOVERY')
$raw=$raw.Replace('GENERIC_LOCALMUTEX_RECOVERY_PUBLICSAFE','GENERIC_FASTSKIP_RECOVERY_PUBLICSAFE')

# Fix FINAL detection on an array of lines.
$badFinal="if (`$tail -notmatch '(^|;)FINAL(;|`$)') { continue }"
$goodFinal="if (-not (`$tail -match '(^|;)FINAL(;|`$)')) { continue }"
if(-not $raw.Contains($badFinal)){throw 'Expected FINAL-detection line not found.'}
$raw=$raw.Replace($badFinal,$goodFinal)

# Critical throughput fix: published pairs must be skipped BEFORE the 20-second stability wait.
$oldBlock=@'
function Publish-Pair([IO.FileInfo]$StatsFile,[string]$TradesPath,$State) {
    $statsPath = $StatsFile.FullName
    $sig1 = (Get-StableSignature $statsPath) + '|' + (Get-StableSignature $TradesPath)
    Start-Sleep -Seconds $StableSeconds
    $sig2 = (Get-StableSignature $statsPath) + '|' + (Get-StableSignature $TradesPath)
    if ($sig1 -ne $sig2) { return $false }

    $statsHash1 = Get-Hash $statsPath
    $tradesHash1 = Get-Hash $TradesPath
    $validated = Validate-Pair $statsPath $TradesPath
    if ($statsHash1 -ne (Get-Hash $statsPath) -or $tradesHash1 -ne (Get-Hash $TradesPath)) {
        throw 'outputs changed during validation.'
    }

    $fingerprint = Get-Fingerprint $statsPath $TradesPath
    if (Is-Published $State $fingerprint) { return $false }
'@
$newBlock=@'
function Publish-Pair([IO.FileInfo]$StatsFile,[string]$TradesPath,$State) {
    $statsPath = $StatsFile.FullName

    # FASTSKIP: existing completed pairs are hashed once and skipped immediately.
    # The expensive stability wait is reserved for an unpublished candidate only.
    $preFingerprint = Get-Fingerprint $statsPath $TradesPath
    if (Is-Published $State $preFingerprint) { return $false }

    $sig1 = (Get-StableSignature $statsPath) + '|' + (Get-StableSignature $TradesPath)
    Start-Sleep -Seconds $StableSeconds
    $sig2 = (Get-StableSignature $statsPath) + '|' + (Get-StableSignature $TradesPath)
    if ($sig1 -ne $sig2) { return $false }

    $statsHash1 = Get-Hash $statsPath
    $tradesHash1 = Get-Hash $TradesPath
    $validated = Validate-Pair $statsPath $TradesPath
    if ($statsHash1 -ne (Get-Hash $statsPath) -or $tradesHash1 -ne (Get-Hash $TradesPath)) {
        throw 'outputs changed during validation.'
    }

    $fingerprint = Get-Fingerprint $statsPath $TradesPath
    if (Is-Published $State $fingerprint) { return $false }
'@
if(-not $raw.Contains($oldBlock)){throw 'Expected Publish-Pair block not found; refusing unsafe patch.'}
$raw=$raw.Replace($oldBlock,$newBlock)

# Create state immediately at watcher start.
$anchor="Set-Content -LiteralPath `$PidFile -Value `$PID -Encoding ASCII"
$replacement=$anchor+"`r`n`$initialState=Load-State`r`nSave-State `$initialState"
if(-not $raw.Contains($anchor)){throw 'PID anchor not found.'}
$raw=$raw.Replace($anchor,$replacement)

Set-Content -LiteralPath $Target -Value $raw -Encoding UTF8

# Static assertions before launch.
$check=Get-Content -LiteralPath $Target -Raw
if($check -notmatch 'FASTSKIP: existing completed pairs'){throw 'FASTSKIP patch missing.'}
if($check -notmatch [regex]::Escape($goodFinal)){throw 'FINAL fix missing.'}
if($check -match 'v203|V203|v2\.03'){throw 'v2.03 residue detected in generated watcher.'}

# Migrate published fingerprints so already-pushed runs are never duplicated.
if((Test-Path -LiteralPath $OldState) -and -not(Test-Path -LiteralPath $NewState)){
    Copy-Item -LiteralPath $OldState -Destination $NewState
    Write-Host "MIGRATE STATE: $OldState -> $NewState"
}

$cmd='@echo off'+"`r`n"+'start "Guardian Backtest CSV Sync v2.04" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$Target+'"'+"`r`n"
Set-Content -LiteralPath $TargetStartup -Value $cmd -Encoding ASCII
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$Target`"")

Start-Sleep -Seconds 2
$active=Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match [regex]::Escape('Guardian_Backtest_CSV_AutoSync_v2_04_GENERIC_FASTSKIP_RECOVERY_PUBLICSAFE.ps1') }
Write-Host "INSTALLE: $Target"
Write-Host "AUTOSTART: $TargetStartup"
Write-Host "ACTIVE V2.04 WATCHERS: $(@($active).Count)"
foreach($p in $active){Write-Host "ACTIVE pid=$($p.ProcessId) | $($p.CommandLine)"}
Write-Host 'HEALTH: D:\MT5_Backtests\guardian-backtest-csv-sync-v204-health.json'
Write-Host 'STATE:  D:\MT5_Backtests\guardian-backtest-csv-sync-v204-state.json'
Write-Host 'LOG:    D:\MT5_Backtests\logs\guardian-backtest-csv-sync-v204.log'
