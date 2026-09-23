$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = "D:\MT5_Backtests"
$Repo = Join-Path $Root "guardian-research"
$SourceEa = Join-Path $Repo "research\ea\D035_FTMO_CFD_M1_Exporter_v1_01.mq5"
$Downstream = Join-Path $Repo "automation\Run-D035F1FTMO2026H1.ps1"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunId = "D035_F1_ONECLICK_$Stamp"
$Work = Join-Path $Root "Research\ExecutionAudit\$RunId"
$Tmp = Join-Path $Work "work"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_D035_F1_FTMO_2026H1_$Stamp.zip"
$CommonRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files\GuardianResearch\SETUP_SCANS\D035_FTMO_CFD_M1_EXPORT"

New-Item -ItemType Directory -Force -Path $Work,$Tmp | Out-Null

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
function Tail([string]$p,[int]$n=4000){
  try{return ((Get-Content $p -Tail $n -ErrorAction Stop) -join [Environment]::NewLine)}
  catch{return ""}
}
function Robo([string]$src,[string]$dst,[string[]]$extra=@()){
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  $args=@($src,$dst,"/E","/R:1","/W:1","/NFL","/NDL","/NJH","/NJS","/NP")+$extra
  & robocopy @args | Out-Null
  if($LASTEXITCODE -gt 7){throw "robocopy failed $src -> $dst ($LASTEXITCODE)"}
}
function LatestExport([string]$sym){
  $dir=Join-Path $CommonRoot $sym
  if(-not (Test-Path $dir)){return $null}
  return Get-ChildItem $dir -Recurse -File -Filter ("D035_CFD_M1_"+$sym+".csv") -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
function VerifyCoverage([System.IO.FileInfo]$f,[string]$sym){
  if(-not $f){throw "Missing $sym export"}
  $first=(Get-Content $f.FullName -TotalCount 2 | Select-Object -Last 1)
  $last=(Get-Content $f.FullName -Tail 1)
  if(-not $first -or -not $last){throw "Empty $sym export"}
  $a=$first -split ';';$b=$last -split ';'
  if($a.Count -lt 21 -or $b.Count -lt 21){throw "Bad $sym export schema"}
  $start=Get-Date -Year ([int]$a[13]) -Month ([int]$a[14]) -Day ([int]$a[15])
  $end=Get-Date -Year ([int]$b[13]) -Month ([int]$b[14]) -Day ([int]$b[15])
  $company=$a[19];$server=$a[20]
  if((($company+" "+$server) -notmatch "(?i)FTMO")){throw "$sym export is not FTMO"}
  if($start -gt [datetime]"2026-01-07" -or $end -lt [datetime]"2026-06-25"){
    throw "$sym export coverage insufficient: $start -> $end"
  }
  Write-Host ("{0}: {1:yyyy-MM-dd} -> {2:yyyy-MM-dd} | {3} | {4}" -f $sym,$start,$end,$company,$server) -ForegroundColor Green
  return [pscustomobject]@{File=$f.FullName;Start=$start;End=$end;Company=$company;Server=$server}
}

Step "1/9 Validate frozen D035-F1 support"
foreach($p in @($SourceEa,$Downstream,
  (Join-Path $Repo "research\campaigns\D035_F1_FTMO_2026H1_HUMAN_AUTHORIZATION_2026_09_23.json"),
  (Join-Path $Repo "research\campaigns\D035_F1_FTMO_TRANSPORT_CONFIRMATION_2026H1_PREREG_2026_09_23.md"))){
  if(-not (Test-Path $p)){throw "Missing support file: $p"}
}
$auth=Get-Content (Join-Path $Repo "research\campaigns\D035_F1_FTMO_2026H1_HUMAN_AUTHORIZATION_2026_09_23.json") -Raw | ConvertFrom-Json
if(-not $auth.authorized_by_owner){throw "D035-F1 authorization guard failed"}
Write-Host "AUTHORIZED: XLMUSD only | SHORT | +15m primary | 2026-H1 only" -ForegroundColor Green
Write-Host "BLOCKED: Jul-Dec 2026 | other targets | retuning | live deployment" -ForegroundColor Yellow

Step "2/9 Find exact running FTMO terminal"
$hits=@()
foreach($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)){
  $title="";$exe=""
  try{$title=$p.MainWindowTitle}catch{}
  try{$exe=$p.Path}catch{}
  if($title -match "(?i)FTMO" -and $exe){$hits += [pscustomobject]@{Id=$p.Id;Title=$title;ExecutablePath=$exe}}
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
if a is None: raise SystemExit("No account info")
names=[s.name for s in (mt5.symbols_get() or [])]
def exact(sym):
    x=[n for n in names if n.upper()==sym]
    return x[0] if x else None
print(json.dumps({"login":int(a.login),"server":str(a.server),"company":str(a.company),
                  "btc":exact("BTCUSD"),"xlm":exact("XLMUSD")}))
mt5.shutdown()
'@
Set-Content $ctxPy $ctxCode -Encoding ASCII
$ctxRaw=& py -3 $ctxPy $live.ExecutablePath
if($LASTEXITCODE -ne 0){throw "Could not read FTMO context"}
$ctx=($ctxRaw | Select-Object -Last 1) | ConvertFrom-Json
if((($ctx.server+" "+$ctx.company) -notmatch "(?i)FTMO")){throw "FTMO identity guard failed"}
if(-not $ctx.btc -or -not $ctx.xlm){throw "FTMO must expose exact BTCUSD and XLMUSD for frozen D035-F1. Context: $ctxRaw"}
Write-Host ("Account {0} | {1} | BTCUSD + XLMUSD available" -f $ctx.login,$ctx.server)

Step "3/9 Resolve live MT5 data folder"
$installDir=Norm (Split-Path $live.ExecutablePath -Parent)
$terminalRoot=Join-Path $env:APPDATA "MetaQuotes\Terminal"
$cands=@()
foreach($d in @(Get-ChildItem $terminalRoot -Directory -ErrorAction SilentlyContinue)){
  if($d.Name -eq "Common"){continue}
  $origin=Join-Path $d.FullName "origin.txt"
  if(-not (Test-Path $origin)){continue}
  $o=Norm (Get-Content $origin -Raw -ErrorAction SilentlyContinue)
  if($o -eq $installDir){$cands += $d.FullName}
}
if($cands.Count -eq 0){throw "No MT5 data folder maps to FTMO install"}
if($cands.Count -eq 1){$dataPath=$cands[0]} else {
  $scored=@()
  foreach($d in $cands){
    $score=0
    foreach($ld in @((Join-Path $d "logs"),(Join-Path $d "MQL5\Logs"))){
      if(Test-Path $ld){
        foreach($f in @(Get-ChildItem $ld -File -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 10)){
          $t=Tail $f.FullName 5000
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

Step "4/9 Prepare isolated portable FTMO clone"
$Portable=Join-Path $Root ("Terminals\FTMO_D035_F1_"+$Stamp)
Robo (Split-Path $live.ExecutablePath -Parent) $Portable @("/XD","MQL5","bases","config","logs","tester","profiles")
Robo (Join-Path $dataPath "config") (Join-Path $Portable "config") @("/MIR")
$sourceBases=Join-Path $dataPath "bases"
if(Test-Path $sourceBases){Robo $sourceBases (Join-Path $Portable "bases") @("/XD","history","ticks")}
Set-Content (Join-Path $Portable "origin.txt") $Portable -Encoding ASCII
$ExpertDir=Join-Path $Portable "MQL5\Experts\GuardianResearch\Backtests"
New-Item -ItemType Directory -Force -Path $ExpertDir | Out-Null

Step "5/9 Compile frozen exporter"
$EaBase="D035_FTMO_CFD_M1_Exporter_v1_01"
$Mq5=Join-Path $ExpertDir ($EaBase+".mq5")
$Ex5=Join-Path $ExpertDir ($EaBase+".ex5")
Copy-Item $SourceEa $Mq5 -Force
$Editor=Join-Path $Portable "metaeditor64.exe"
$Terminal=Join-Path $Portable "terminal64.exe"
$CompileLog=Join-Path $Tmp "compile.log"
$compileArgs=('/portable /compile:"{0}" /log:"{1}"' -f $Mq5,$CompileLog)
Start-Process -FilePath $Editor -ArgumentList $compileArgs | Out-Null
$deadline=(Get-Date).AddSeconds(120)
while(-not (Test-Path $Ex5)){
  $ct=Tail $CompileLog 1000
  if($ct -match '(?i)Result:\s*[1-9][0-9]*\s+errors?' -or $ct -match '(?i)error\s+[0-9]+:'){
    throw "Compile failed. "+$ct
  }
  if((Get-Date)-gt $deadline){throw "Compile timeout. "+$ct}
  Start-Sleep -Milliseconds 500
}
$ct=Tail $CompileLog 1000
if($ct -match '(?i)Result:\s*[1-9][0-9]*\s+errors?' -or $ct -match '(?i)error\s+[0-9]+:'){
  throw "Compile failed. "+$ct
}

Step "6/9 Export frozen FTMO M1 BTCUSD + XLMUSD, 2026-H1"
$ExpertRelative="GuardianResearch\Backtests\$EaBase"
$exports=@{}
foreach($sym in @("BTCUSD","XLMUSD")){
  Write-Host ""
  Write-Host ("--- EXPORT "+$sym+" ---") -ForegroundColor Yellow
  $before=LatestExport $sym
  $beforeTime=if($before){$before.LastWriteTime}else{[datetime]::MinValue}

  $Ini=Join-Path $Tmp ("tester_"+$sym+".ini")
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
Symbol=$sym
Period=M1
Model=1
ExecutionMode=0
Optimization=0
FromDate=2026.01.01
ToDate=2026.07.01
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
  $limit=(Get-Date).AddMinutes(180)
  $lastPrint=(Get-Date)
  while(-not $proc.HasExited){
    if((Get-Date)-gt $limit){try{Stop-Process $proc.Id -Force}catch{};throw "$sym exporter timeout"}
    if(((Get-Date)-$lastPrint).TotalSeconds -ge 20){
      Write-Host ("{0} export running..." -f $sym)
      $lastPrint=Get-Date
    }
    Start-Sleep -Seconds 2
    try{$proc.Refresh()}catch{}
  }
  if($proc.ExitCode -ne 0){Write-Host ("Warning: tester exit code "+$proc.ExitCode) -ForegroundColor Yellow}
  Start-Sleep -Seconds 2

  $f=LatestExport $sym
  if(-not $f -or $f.LastWriteTime -le $beforeTime){throw "No new $sym export detected"}
  $exports[$sym]=VerifyCoverage $f $sym
}

Step "7/9 Run frozen D035-F1 analyzer"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Downstream -Root $Root 2>&1 | Tee-Object -FilePath (Join-Path $Work "D035_F1_ANALYSIS.log")
if($LASTEXITCODE -ne 0){throw "D035-F1 analyzer failed with exit code $LASTEXITCODE"}

$resultDir=Join-Path $Root "Research\Autonomous\d035_f1_ftmo_2026h1\result"
$resultFile=Join-Path $resultDir "D035_F1_RESULT.json"
if(-not (Test-Path $resultFile)){throw "D035_F1_RESULT.json missing after analyzer"}

Step "8/9 Copy receipt"
Copy-Item $resultFile (Join-Path $Work "D035_F1_RESULT.json") -Force
foreach($n in @("D035_F1_FTMO_XLM_EVENT_RETURNS.csv","D035_F1_CAUSAL_DUAL_EVENTS.csv","D035_F1_OFFSET_QA.csv")){
  $p=Join-Path $resultDir $n
  if(Test-Path $p){Copy-Item $p (Join-Path $Work $n) -Force}
}
[ordered]@{
  run_id=$RunId
  authorization="D035_F1_FTMO_2026H1_HUMAN_AUTHORIZATION_2026_09_23.json"
  target="XLMUSD"
  direction="SHORT"
  primary_horizon_min=15
  diagnostic_horizon_min=30
  ftmo_commission_rate_per_side=0.000325
  window="2026-01-01 through 2026-06-30 UTC"
  btc_export=$exports["BTCUSD"].File
  xlm_export=$exports["XLMUSD"].File
  jul_dec_2026_opened=$false
  other_targets_opened=$false
  retuning_performed=$false
} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Work "RUN_INFO.json") -Encoding UTF8

Step "9/9 Zip"
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Work\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
Write-Host ""
Write-Host "=== D035-F1 COMPLETE ===" -ForegroundColor Green
Write-Host ("ZIP: "+$Zip) -ForegroundColor Green
Write-Host "Jul-Dec 2026 NOT opened | other targets NOT opened | no retuning" -ForegroundColor Yellow
try{Remove-Item $Portable -Recurse -Force -ErrorAction SilentlyContinue}catch{}
