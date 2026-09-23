$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = "D:\MT5_Backtests\guardian-research"
$SourceEa = Join-Path $Repo "research\ea\D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5"
$Analyzer = Join-Path $Repo "tools\analyze_d017_btc_sell_2p5r_ftmo_v1_00.py"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunId = "D017_BTC_SELL_2P5R_FTMO_$Stamp"
$Work = "D:\MT5_Backtests\Research\ExecutionAudit\$RunId"
$Raw = Join-Path $Work "raw"
$Analysis = Join-Path $Work "analysis"
$Tmp = Join-Path $Work "work"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_D017_BTC_SELL_2P5R_FTMO_$Stamp.zip"
$Common = Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files"
$RelOutput = "GuardianResearch\D017Momentum\FTMO\$RunId"
$CommonOut = Join-Path $Common $RelOutput

New-Item -ItemType Directory -Force -Path $Raw,$Analysis,$Tmp | Out-Null
if(Test-Path $CommonOut){Remove-Item $CommonOut -Recurse -Force}

function Step([string]$s){
  Write-Host ""
  Write-Host ("=== "+$s+" ===") -ForegroundColor Cyan
}
function Norm([string]$p){
  if(-not $p){return ""}
  try{
    if(Test-Path $p -PathType Leaf){$p=Split-Path $p -Parent}
    return ([IO.Path]::GetFullPath($p)).TrimEnd("\").ToLowerInvariant()
  }catch{return $p.TrimEnd("\").ToLowerInvariant()}
}
function Tail([string]$p,[int]$n=5000){
  try{return ((Get-Content $p -Tail $n -ErrorAction Stop) -join [Environment]::NewLine)}
  catch{return ""}
}
function Robo([string]$src,[string]$dst,[string[]]$extra=@()){
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  $args=@($src,$dst,"/E","/R:1","/W:1","/NFL","/NDL","/NJH","/NJS","/NP")+$extra
  & robocopy @args | Out-Null
  if($LASTEXITCODE -gt 7){throw "robocopy failed $src -> $dst ($LASTEXITCODE)"}
}

Step "1/9 Find exact running FTMO terminal"
$hits=@()
foreach($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)){
  $title="";$exe=""
  try{$title=$p.MainWindowTitle}catch{}
  try{$exe=$p.Path}catch{}
  if($title -match "(?i)FTMO" -and $exe){
    $hits += [pscustomobject]@{Id=$p.Id;Title=$title;ExecutablePath=$exe}
  }
}
if($hits.Count -ne 1){
  $hits | Format-Table -AutoSize | Out-Host
  throw "Expected exactly one running FTMO MT5 window; found $($hits.Count)."
}
$live=$hits[0]
Write-Host ("LIVE: "+$live.Title) -ForegroundColor Green

$ctxPy=Join-Path $Tmp "ftmo_context.py"
$ctxCode=@'
import json,sys
import MetaTrader5 as mt5
exe=sys.argv[1]
if not mt5.initialize(path=exe):
    raise SystemExit("MT5 init failed: "+str(mt5.last_error()))
a=mt5.account_info()
if a is None:
    raise SystemExit("No account info")
names=[s.name for s in (mt5.symbols_get() or [])]
exact=[n for n in names if n.upper()=="BTCUSD"]
pref=[n for n in names if n.upper().startswith("BTCUSD")]
contains=[n for n in names if "BTC" in n.upper() and "USD" in n.upper()]
sym=(exact or pref or contains or [None])[0]
print(json.dumps({"login":int(a.login),"server":str(a.server),"company":str(a.company),"name":str(a.name),"symbol":sym}))
mt5.shutdown()
'@
Set-Content $ctxPy $ctxCode -Encoding ASCII
$ctxRaw=& py -3 $ctxPy $live.ExecutablePath
if($LASTEXITCODE -ne 0){throw "Could not read FTMO account context."}
$ctx=($ctxRaw | Select-Object -Last 1) | ConvertFrom-Json
if((($ctx.server+" "+$ctx.company) -notmatch "(?i)FTMO") -or -not $ctx.symbol){throw "FTMO/BTC symbol guard failed: $ctxRaw"}
Write-Host ("Account: {0} | Server: {1} | Symbol: {2}" -f $ctx.login,$ctx.server,$ctx.symbol)

Step "2/9 Resolve live MT5 data folder"
$installDir=Norm (Split-Path $live.ExecutablePath -Parent)
$root=Join-Path $env:APPDATA "MetaQuotes\Terminal"
$cands=@()
foreach($d in @(Get-ChildItem $root -Directory -ErrorAction SilentlyContinue)){
  if($d.Name -eq "Common"){continue}
  $origin=Join-Path $d.FullName "origin.txt"
  if(-not (Test-Path $origin)){continue}
  $o=Norm (Get-Content $origin -Raw -ErrorAction SilentlyContinue)
  if($o -eq $installDir){$cands += $d.FullName}
}
if($cands.Count -eq 0){throw "No MT5 data folder maps to FTMO install $installDir"}
if($cands.Count -eq 1){
  $dataPath=$cands[0]
}else{
  $scored=@()
  foreach($d in $cands){
    $score=0
    foreach($ld in @((Join-Path $d "logs"),(Join-Path $d "MQL5\Logs"))){
      if(Test-Path $ld){
        foreach($f in @(Get-ChildItem $ld -File -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 10)){
          $t=Tail $f.FullName 6000
          if($t -match [regex]::Escape([string]$ctx.login)){$score+=10}
          if($t -match [regex]::Escape([string]$ctx.server)){$score+=5}
        }
      }
    }
    $scored += [pscustomobject]@{Path=$d;Score=$score}
  }
  $dataPath=($scored | Sort-Object Score -Descending | Select-Object -First 1).Path
}
Write-Host ("Data path: "+$dataPath)

Step "3/9 Prepare isolated portable FTMO clone"
$Portable="D:\MT5_Backtests\Terminals\FTMO_D017_BTC_$Stamp"
Robo (Split-Path $live.ExecutablePath -Parent) $Portable @("/XD","MQL5","bases","config","logs","tester","profiles")
Robo (Join-Path $dataPath "config") (Join-Path $Portable "config") @("/MIR")
$sourceBases=Join-Path $dataPath "bases"
if(Test-Path $sourceBases){Robo $sourceBases (Join-Path $Portable "bases") @("/XD","history","ticks")}
Set-Content (Join-Path $Portable "origin.txt") $Portable -Encoding ASCII
$ExpertDir=Join-Path $Portable "MQL5\Experts\GuardianResearch\Backtests"
New-Item -ItemType Directory -Force -Path $ExpertDir | Out-Null

Step "4/9 Generate run-specific D017 harness"
if(-not (Test-Path $SourceEa)){throw "Missing source EA $SourceEa"}
$src=Get-Content $SourceEa -Raw
$base="GuardianResearch\\D017Momentum\\FTMO\\$RunId"
$nl=[Environment]::NewLine

$folderNeedle='FolderCreate("GuardianResearch\\D017Momentum",FILE_COMMON);'
$folderReplacement='FolderCreate("GuardianResearch\\D017Momentum",FILE_COMMON);'+$nl+'   FolderCreate("GuardianResearch\\D017Momentum\\FTMO",FILE_COMMON);'+$nl+'   FolderCreate("'+$base+'",FILE_COMMON);'
$src=$src.Replace($folderNeedle,$folderReplacement)

$src=$src.Replace('string EventsFile(){return "GuardianResearch\\D017Momentum\\d017_momentum_virtual_events.csv";}','string EventsFile(){return "'+$base+'\\events.csv";}')
$src=$src.Replace('string TradesFile(){return "GuardianResearch\\D017Momentum\\d017_momentum_virtual_trades.csv";}','string TradesFile(){return "'+$base+'\\trades.csv";}')
$src=$src.Replace('string OutcomesFile(){return "GuardianResearch\\D017Momentum\\d017_momentum_virtual_outcomes.csv";}','string OutcomesFile(){return "'+$base+'\\outcomes.csv";}')

$oldDeinit='void OnDeinit(const int reason){if(g_atr!=INVALID_HANDLE)IndicatorRelease(g_atr);if(g_adx!=INVALID_HANDLE)IndicatorRelease(g_adx);if(g_macro_ema!=INVALID_HANDLE)IndicatorRelease(g_macro_ema);if(g_macro_atr!=INVALID_HANDLE)IndicatorRelease(g_macro_atr);if(g_dir_ema!=INVALID_HANDLE)IndicatorRelease(g_dir_ema);}'
$newDeinit='void OnDeinit(const int reason){if(g_atr!=INVALID_HANDLE)IndicatorRelease(g_atr);if(g_adx!=INVALID_HANDLE)IndicatorRelease(g_adx);if(g_macro_ema!=INVALID_HANDLE)IndicatorRelease(g_macro_ema);if(g_macro_atr!=INVALID_HANDLE)IndicatorRelease(g_macro_atr);if(g_dir_ema!=INVALID_HANDLE)IndicatorRelease(g_dir_ema); int h=FileOpen("'+$base+'\\COMPLETE.txt",FILE_WRITE|FILE_TXT|FILE_COMMON|FILE_ANSI); if(h!=INVALID_HANDLE){FileWrite(h,"run_id='+$RunId+'");FileWrite(h,"reason="+IntegerToString(reason));FileClose(h);}}'
if(-not $src.Contains($oldDeinit)){throw "D017 OnDeinit source block changed; refusing unknown patch."}
$src=$src.Replace($oldDeinit,$newDeinit)

$EaBase="D017_BTC_SELL_2P5R_FTMO_$Stamp"
$Mq5=Join-Path $ExpertDir ($EaBase+".mq5")
$Ex5=Join-Path $ExpertDir ($EaBase+".ex5")
Set-Content $Mq5 $src -Encoding UTF8

Step "5/9 Compile"
$Editor=Join-Path $Portable "metaeditor64.exe"
$Terminal=Join-Path $Portable "terminal64.exe"
$CompileLog=Join-Path $Tmp "compile.log"
$compileArgs=('/portable /compile:"{0}" /log:"{1}"' -f $Mq5,$CompileLog)
Start-Process -FilePath $Editor -ArgumentList $compileArgs | Out-Null
$deadline=(Get-Date).AddSeconds(120)
while(-not (Test-Path $Ex5)){
  if((Get-Date)-gt $deadline){throw "Compile timeout. "+(Tail $CompileLog 500)}
  Start-Sleep -Milliseconds 500
}
if((Tail $CompileLog 1000) -match '(?i)([1-9][0-9]*)\s+error'){throw "Compile errors: "+(Tail $CompileLog 1000)}

Step "6/9 Run FTMO Strategy Tester 2023-2025"
$Ini=Join-Path $Tmp "tester.ini"
$ExpertRelative="GuardianResearch\Backtests\$EaBase"
$iniText=@"
[Common]
Login=$($ctx.login)
Server=$($ctx.server)
KeepPrivate=1
NewsEnable=0

[Experts]
AllowLiveTrading=0
AllowDllImport=0

[Tester]
Expert=$ExpertRelative
Symbol=$($ctx.symbol)
Period=M1
Model=1
ExecutionMode=0
Optimization=0
FromDate=2023.01.01
ToDate=2025.12.31
ForwardMode=0
Deposit=100000
Currency=USD
Leverage=1:100
ReplaceReport=1
ShutdownTerminal=1
"@
Set-Content $Ini $iniText -Encoding ASCII
$terminalArgs=('/portable /config:"{0}"' -f $Ini)
$proc=Start-Process -FilePath $Terminal -ArgumentList $terminalArgs -PassThru

$verify=(Get-Date).AddMinutes(3)
$confirmed=$false
while((Get-Date)-lt $verify){
  foreach($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)){
    $path="";$title=""
    try{$path=$p.Path}catch{}
    try{$title=$p.MainWindowTitle}catch{}
    if($path -and $path.StartsWith($Portable,[System.StringComparison]::OrdinalIgnoreCase)){
      if($title -match [regex]::Escape([string]$ctx.login) -or $title -match [regex]::Escape([string]$ctx.server)){$confirmed=$true}
    }
  }
  if($confirmed){break}
  $logs=Join-Path $Portable "logs"
  if(Test-Path $logs){
    foreach($f in @(Get-ChildItem $logs -File -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 5)){
      $t=Tail $f.FullName 6000
      if($t -match [regex]::Escape([string]$ctx.login)){$confirmed=$true;break}
    }
  }
  if($confirmed){break}
  Start-Sleep -Seconds 2
}
if(-not $confirmed){
  try{if(-not $proc.HasExited){Stop-Process $proc.Id -Force}}catch{}
  throw "Portable FTMO account confirmation failed."
}
Write-Host "FTMO portable account confirmed." -ForegroundColor Green

$runDeadline=(Get-Date).AddMinutes(360)
$last=(Get-Date)
while(-not (Test-Path (Join-Path $CommonOut "COMPLETE.txt"))){
  if((Get-Date)-gt $runDeadline){throw "Tester timeout after 360 minutes."}
  if(((Get-Date)-$last).TotalSeconds -ge 30){Write-Host "D017 BTC backtest running...";$last=Get-Date}
  Start-Sleep -Seconds 3
}

Step "7/9 Collect raw results"
foreach($n in @("events.csv","trades.csv","outcomes.csv","COMPLETE.txt")){
  $p=Join-Path $CommonOut $n
  if(Test-Path $p){Copy-Item $p (Join-Path $Raw $n) -Force}
}
if(-not (Test-Path (Join-Path $Raw "trades.csv"))){throw "trades.csv missing"}
if(-not (Test-Path (Join-Path $Raw "outcomes.csv"))){throw "outcomes.csv missing"}
if(-not (Test-Path (Join-Path $Raw "events.csv"))){throw "events.csv missing"}

Step "8/9 Analyze frozen BTC SELL +2.5R"
& py -3 $Analyzer --raw $Raw --out $Analysis 2>&1 | Tee-Object -FilePath (Join-Path $Work "ANALYSIS.log")
if($LASTEXITCODE -ne 0){throw "Analyzer failed."}
Copy-Item $Ini (Join-Path $Work "tester.ini") -Force
Copy-Item $CompileLog (Join-Path $Work "compile.log") -Force -ErrorAction SilentlyContinue
$runInfo=[ordered]@{
  run_id=$RunId
  ftmo_login=$ctx.login
  ftmo_server=$ctx.server
  symbol=$ctx.symbol
  from="2023.01.01"
  to="2025.12.31"
  model="1 minute OHLC"
  source="D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5"
  protected_2026_accessed=$false
}
$runInfo | ConvertTo-Json | Set-Content (Join-Path $Work "RUN_INFO.json") -Encoding UTF8

Step "9/9 Zip"
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Work\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
Write-Host ("ZIP: "+$Zip) -ForegroundColor Green
try{Remove-Item $Portable -Recurse -Force -ErrorAction SilentlyContinue}catch{}
