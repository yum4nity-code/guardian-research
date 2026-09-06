param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Once,
    [int]$PollSeconds = 5,
    [int]$StableSeconds = 20,
    [int]$GitAttempts = 5
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$TaskLabel='Guardian Backtest CSV AutoSync v2.00 GENERIC PUBLICSAFE'
$InstallDir='D:\MT5_Backtests\automation'
$InstalledFile=Join-Path $InstallDir 'Guardian_Backtest_CSV_AutoSync_v2_00_GENERIC_PUBLICSAFE.ps1'
$StartupDir=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$StartupCmd=Join-Path $StartupDir 'Guardian_Backtest_CSV_AutoSync_v2_00.cmd'
$PidFile='D:\MT5_Backtests\guardian-backtest-csv-sync-v200.pid'
$StateFile='D:\MT5_Backtests\guardian-backtest-csv-sync-v200-state.json'
$HealthFile='D:\MT5_Backtests\guardian-backtest-csv-sync-v200-health.json'
$LogFile='D:\MT5_Backtests\logs\guardian-backtest-csv-sync-v200.log'
$ResultsClone='D:\MT5_Backtests\guardian-backtest-autosync-results'
$ResultsBranch='backtest-results'
$RepoRoot='D:\MT5_Backtests\guardian-research'
$RemoteFallback='https://github.com/yum4nity-code/guardian-research.git'
$CommonFiles=Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$OldStartupV104=Join-Path $StartupDir 'Guardian_D023_CSV_AutoSync_v1_04.cmd'
$OldPidV104='D:\MT5_Backtests\guardian-d023-csv-sync-v104.pid'

function Ensure-Parent([string]$Path){$p=Split-Path -Parent $Path;if($p -and -not(Test-Path -LiteralPath $p)){New-Item -ItemType Directory -Force -Path $p|Out-Null}}
function Log([string]$m){Ensure-Parent $LogFile;$line='{0} | {1}' -f ([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')),$m;Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8;if(-not $Install){Write-Host $line}}
function Health([string]$status,[string]$message,[string]$file=''){Ensure-Parent $HealthFile;[ordered]@{schema=2;watcher=$TaskLabel;updated_at_utc=[DateTime]::UtcNow.ToString('o');status=$status;message=$message;last_file=$file;common_files=$CommonFiles;results_branch=$ResultsBranch}|ConvertTo-Json -Depth 4|Set-Content "$HealthFile.tmp" -Encoding UTF8;Move-Item "$HealthFile.tmp" $HealthFile -Force}

function QuoteArg([string]$v){if($null -eq $v -or $v.Length -eq 0){return '""'};if($v -notmatch '[\s"]'){return $v};return '"'+($v -replace '(\\*)"','$1$1\"' -replace '(\\+)$','$1$1')+'"'}
function GitOnce([string[]]$GitArgs,[switch]$AllowFailure){
    if(-not $GitArgs -or $GitArgs.Count -eq 0){throw 'empty GitArgs'}
    $git=(Get-Command git.exe -ErrorAction Stop).Source
    $o=Join-Path $env:TEMP ("guardian_git_o_{0}_{1}.txt" -f $PID,[guid]::NewGuid().ToString('N'))
    $e=Join-Path $env:TEMP ("guardian_git_e_{0}_{1}.txt" -f $PID,[guid]::NewGuid().ToString('N'))
    try{
        $line=(($GitArgs|ForEach-Object{QuoteArg $_}) -join ' ')
        $p=Start-Process -FilePath $git -ArgumentList $line -NoNewWindow -Wait -PassThru -RedirectStandardOutput $o -RedirectStandardError $e
        $so=if(Test-Path $o){@(Get-Content $o -ErrorAction SilentlyContinue)}else{@()};$se=if(Test-Path $e){@(Get-Content $e -ErrorAction SilentlyContinue)}else{@()};$all=@($so)+@($se)
        if($p.ExitCode -ne 0 -and -not $AllowFailure){throw "git $($GitArgs -join ' ') failed ($($p.ExitCode)): $($all -join ' ')"}
        return [pscustomobject]@{Code=$p.ExitCode;StdOut=@($so);StdErr=@($se);Output=@($all)}
    }finally{Remove-Item $o,$e -Force -ErrorAction SilentlyContinue}
}
function GitRetry([string[]]$GitArgs){for($i=1;$i -le [Math]::Max(1,$GitAttempts);$i++){$r=GitOnce -GitArgs $GitArgs -AllowFailure;if($r.Code -eq 0){return $r};if($i -ge $GitAttempts){throw "git failed after $GitAttempts attempts: $($r.Output -join ' ')"};Start-Sleep -Seconds ([int][Math]::Min(60,[Math]::Pow(2,$i)))}}
function RemoteUrl{if(Test-Path (Join-Path $RepoRoot '.git')){try{$r=GitOnce @('-C',$RepoRoot,'remote','get-url','origin');$u=(($r.StdOut|Select-Object -First 1).ToString()).Trim();if($u){return $u}}catch{}};return $RemoteFallback}
function EnsureClone{
    if(-not(Get-Command git.exe -ErrorAction SilentlyContinue)){throw 'git.exe introuvable'}
    if(-not(Test-Path (Join-Path $ResultsClone '.git'))){if(Test-Path $ResultsClone){Move-Item $ResultsClone "$ResultsClone.bad.$([DateTime]::Now.ToString('yyyyMMdd_HHmmss'))"};$remote=RemoteUrl;GitRetry @('clone','--quiet','--branch',$ResultsBranch,'--single-branch',$remote,$ResultsClone)|Out-Null}
    $dirty=GitOnce @('-C',$ResultsClone,'status','--porcelain')
    if(@($dirty.StdOut).Count -gt 0){GitRetry @('-C',$ResultsClone,'add','-A')|Out-Null;$c=GitOnce @('-C',$ResultsClone,'commit','-m','Recover pending generic autosync transaction') -AllowFailure;if($c.Code -eq 0){GitRetry @('-C',$ResultsClone,'push','origin',$ResultsBranch)|Out-Null}}
    GitRetry @('-C',$ResultsClone,'pull','--rebase','origin',$ResultsBranch)|Out-Null
}
function Hash([string]$p){(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}
function Sig([string]$p){$f=Get-Item $p;'{0}|{1}' -f $f.Length,$f.LastWriteTimeUtc.Ticks}
function Fingerprint([string]$a,[string]$b){$s="$a|$(Hash $a)|$b|$(Hash $b)";$sha=[Security.Cryptography.SHA256]::Create();try{(($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s))|ForEach-Object{$_.ToString('x2')}) -join '')}finally{$sha.Dispose()}}

function LoadState{
    if(Test-Path $StateFile){try{return Get-Content $StateFile -Raw|ConvertFrom-Json}catch{}}
    return [pscustomobject]@{schema=2;watch_start_utc=[DateTime]::UtcNow.ToString('o');published_fingerprints=@()}
}
function SaveState($state){Ensure-Parent $StateFile;$state|ConvertTo-Json -Depth 8|Set-Content "$StateFile.tmp" -Encoding UTF8;Move-Item "$StateFile.tmp" $StateFile -Force}
function IsPublished($state,[string]$fp){return @($state.published_fingerprints) -contains $fp}
function MarkPublished($state,[string]$fp){$state.published_fingerprints=@(@($state.published_fingerprints)+$fp|Select-Object -Unique);SaveState $state}

function ValidatePair([string]$stats,[string]$trades){
    $ss=@(Import-Csv $stats -Delimiter ';');if($ss.Count -lt 3){throw 'STATS incomplete'}
    $st=@($ss|ForEach-Object{$_.status});$i=[Array]::IndexOf($st,'INIT');$r=[Array]::IndexOf($st,'READY');$f=[Array]::LastIndexOf($st,'FINAL')
    if($i -lt 0 -or $r -lt 0 -or $f -lt 0 -or -not($i -lt $r -and $r -lt $f)){throw 'require INIT -> READY -> FINAL'}
    $final=$ss[$f]
    foreach($field in @('source_name','source_version','symbol','timeframe','trades_closed','csv_trade_rows')){if(-not($final.PSObject.Properties.Name -contains $field) -or -not $final.$field){throw "missing final field $field"}}
    $closed=0;$rows=0;if(-not[int]::TryParse($final.trades_closed,[ref]$closed)){throw 'invalid trades_closed'};if(-not[int]::TryParse($final.csv_trade_rows,[ref]$rows)){throw 'invalid csv_trade_rows'};if($closed -ne $rows){throw "counter mismatch $closed/$rows"}
    $tt=@(Import-Csv $trades -Delimiter ';');if($tt.Count -ne $closed){throw "TRADES row mismatch $($tt.Count)/$closed"}
    return [pscustomobject]@{Final=$final;Trades=$tt;Closed=$closed}
}
function PublicCopy([string]$src,[string]$dst,[switch]$Redact){Ensure-Parent $dst;$raw=Get-Content $src -Raw;if($Redact){$raw=[regex]::Replace($raw,'(?i)([A-Z]:\\Users\\)[^\\;,"\r\n]+','$1<REDACTED>')};foreach($rx in @('(?i)password','(?i)api[_-]?key','(?i)secret','(?i)credential','(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}')){if($raw -match $rx){throw "PUBLICSAFE block $([IO.Path]::GetFileName($src))"}};if($raw -match '(?i)[A-Z]:\\Users\\(?!<REDACTED>)[^\\;,"\r\n]+'){throw 'unredacted Windows user path'};Set-Content $dst -Value $raw -Encoding UTF8}

function PublishPair([IO.FileInfo]$sf,[string]$tp,$state){
    $sp=$sf.FullName;$s1=Sig $sp;$t1=Sig $tp;Start-Sleep -Seconds $StableSeconds;if($s1 -ne (Sig $sp) -or $t1 -ne (Sig $tp)){return}
    $h1=Hash $sp;$h2=Hash $tp;$v=ValidatePair $sp $tp;if($h1 -ne (Hash $sp) -or $h2 -ne (Hash $tp)){throw 'outputs changed during validation'}
    $fp=Fingerprint $sp $tp;if(IsPublished $state $fp){return}
    EnsureClone
    $family=([regex]::Match($sf.Name,'^(D\d{3})_')).Groups[1].Value;if(-not $family){$family='DXXX'}
    $sym=($v.Final.symbol -replace '[^A-Za-z0-9_-]','_');$stamp=$sf.LastWriteTimeUtc.ToString('yyyyMMdd_HHmmss');$runId="${stamp}_${family}_${sym}_$($fp.Substring(0,12))"
    $rel='backtests/inbox/{0}/{1}/{2}/{3}' -f $sf.LastWriteTimeUtc.ToString('yyyy'),$sf.LastWriteTimeUtc.ToString('MM'),$sf.LastWriteTimeUtc.ToString('dd'),$runId;$dest=Join-Path $ResultsClone ($rel -replace '/','\');New-Item -ItemType Directory -Force -Path $dest|Out-Null
    $sd=Join-Path $dest $sf.Name;$td=Join-Path $dest ([IO.Path]::GetFileName($tp));PublicCopy $sp $sd -Redact;PublicCopy $tp $td
    $vv=ValidatePair $sd $td
    $stage=if($v.Final.PSObject.Properties.Name -contains 'run_stage'){$v.Final.run_stage}else{''}
    [ordered]@{schema=5;run_id=$runId;fingerprint=$fp;synced_at_utc=[DateTime]::UtcNow.ToString('o');reason='GENERIC_FINAL_VALIDATED';branch=$ResultsBranch;autosync_version='2.00';validation=[ordered]@{required_status_sequence='INIT -> READY -> FINAL';source_name=$v.Final.source_name;source_version=$v.Final.source_version;run_stage=$stage;symbol=$v.Final.symbol;timeframe=$v.Final.timeframe;trades_closed=$vv.Closed;published_trades_rows=$vv.Trades.Count};files=@([ordered]@{name=$sf.Name;source_sha256=$h1;published_sha256=(Hash $sd);sanitized=$true},[ordered]@{name=[IO.Path]::GetFileName($tp);source_sha256=$h2;published_sha256=(Hash $td);sanitized=$false})}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $dest 'sync_manifest.json') -Encoding UTF8
    [ordered]@{schema=5;synced_at_utc=[DateTime]::UtcNow.ToString('o');run_id=$runId;path=$rel;fingerprint=$fp;reason='GENERIC_FINAL_VALIDATED';files=@($sf.Name,[IO.Path]::GetFileName($tp),'sync_manifest.json')}|ConvertTo-Json -Depth 6|Set-Content (Join-Path $ResultsClone 'backtests\inbox\LATEST.json') -Encoding UTF8
    GitRetry @('-C',$ResultsClone,'config','user.name','Guardian Backtest Bot')|Out-Null;GitRetry @('-C',$ResultsClone,'config','user.email','guardian-backtest@local')|Out-Null;GitRetry @('-C',$ResultsClone,'add','backtests/inbox')|Out-Null;GitRetry @('-C',$ResultsClone,'commit','-m',"Auto-sync validated $family CSV $runId")|Out-Null;GitRetry @('-C',$ResultsClone,'push','origin',$ResultsBranch)|Out-Null
    MarkPublished $state $fp;Health 'OK' "PUSH OK $runId" $sf.Name;Log "PUSH OK | $runId | source=$($v.Final.source_name) | rows=$($v.Closed)"
}

function Cycle{
    $state=LoadState;$start=[DateTime]::Parse($state.watch_start_utc).ToUniversalTime();$files=@(Get-ChildItem $CommonFiles -File -Filter 'D*_STATS.csv' -ErrorAction SilentlyContinue|Where-Object{$_.Name -match '^D\d{3}_V.+_STATS\.csv$' -and $_.LastWriteTimeUtc -ge $start}|Sort-Object LastWriteTimeUtc)
    if($files.Count -eq 0){Health 'WAITING_OUTPUTS' 'No new finalized Dxxx STATS/TRADES pair yet.';return}
    foreach($sf in $files){$tn=$sf.Name -replace '_STATS\.csv$','_TRADES.csv';$tp=Join-Path $CommonFiles $tn;if(-not(Test-Path $tp)){continue};try{PublishPair $sf $tp $state}catch{Health 'ERROR_RETRYING' $_.Exception.Message $sf.Name;Log "ERROR cycle | $($sf.Name) | $($_.Exception.Message)"}}
}

function StopPid([string]$pf){if(Test-Path $pf){try{$p=[int](Get-Content $pf -Raw);Stop-Process -Id $p -Force -ErrorAction SilentlyContinue}catch{};Remove-Item $pf -Force -ErrorAction SilentlyContinue}}
if($Uninstall){StopPid $PidFile;Remove-Item $StartupCmd -Force -ErrorAction SilentlyContinue;Write-Host 'Guardian generic AutoSync v2.00 uninstalled.';exit}
if($Install){
    New-Item -ItemType Directory -Force -Path $InstallDir,$StartupDir|Out-Null;Copy-Item $PSCommandPath $InstalledFile -Force
    StopPid $OldPidV104;Remove-Item $OldStartupV104 -Force -ErrorAction SilentlyContinue;StopPid $PidFile
    [ordered]@{schema=2;watch_start_utc=[DateTime]::UtcNow.AddSeconds(-5).ToString('o');published_fingerprints=@()}|ConvertTo-Json|Set-Content $StateFile -Encoding UTF8
    $cmd='@echo off'+[Environment]::NewLine+'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$InstalledFile+'"';Set-Content $StartupCmd -Value $cmd -Encoding ASCII
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$InstalledFile)
    Write-Host "INSTALLE: $InstalledFile";Write-Host "AUTOSTART: $StartupCmd";Write-Host "HEALTH: $HealthFile";Write-Host "LOG: $LogFile";exit
}

$created=$false;$mutex=New-Object Threading.Mutex($true,'Global\GuardianBacktestCSVAutoSyncV200',[ref]$created);if(-not $created){exit}
try{Set-Content $PidFile -Value $PID -Encoding ASCII;Health 'STARTING' 'Generic watcher started.';Log "START | pid=$PID | common=$CommonFiles";if($Once){Cycle}else{while($true){Cycle;Start-Sleep -Seconds $PollSeconds}}}finally{Remove-Item $PidFile -Force -ErrorAction SilentlyContinue;$mutex.ReleaseMutex();$mutex.Dispose();Log 'STOP'}
