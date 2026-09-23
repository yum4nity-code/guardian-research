$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Repo = "D:\MT5_Backtests\guardian-research"
$SourceEa = Join-Path $Repo "research\ea\D032_C1_CONFIRM_DojiStar_H1_v1_00.mq5"
$Analyzer = Join-Path $Repo "tools\analyze_d032_exact_ftmo_parity_v1_00.py"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunId = "D032_EXACT_FTMO_$Stamp"
$Work = "D:\MT5_Backtests\Research\ExecutionAudit\$RunId"
$Runs = Join-Path $Work "runs"
$Tmp = Join-Path $Work "work"
$Analysis = Join-Path $Work "analysis"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "GUARDIAN_D032_EXACT_FTMO_PARITY_$Stamp.zip"
$Common = Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files"

New-Item -ItemType Directory -Force -Path $Runs,$Tmp,$Analysis | Out-Null

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

Step "1/8 Find exact running FTMO terminal"
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
if a is None: raise SystemExit("No account info")
names=[s.name for s in (mt5.symbols_get() or [])]
def pick(key):
    exact=[n for n in names if n.upper()==key]
    pref=[n for n in names if n.upper().startswith(key)]
    return (exact or pref or [None])[0]
btc=pick("BTCUSD")
eth=pick("ETHUSD")
dog=pick("DOGEUSD") or pick("DOGUSD")
print(json.dumps({"login":int(a.login),"server":str(a.server),"company":str(a.company),"btc":btc,"eth":eth,"dog":dog}))
mt5.shutdown()
'@
Set-Content $ctxPy $ctxCode -Encoding ASCII
$ctxRaw=& py -3 $ctxPy $live.ExecutablePath
if($LASTEXITCODE -ne 0){throw "Could not read FTMO account context."}
$ctx=($ctxRaw | Select-Object -Last 1) | ConvertFrom-Json
if((($ctx.server+" "+$ctx.company) -notmatch "(?i)FTMO")){throw "FTMO guard failed."}
if(-not $ctx.btc -or -not $ctx.eth -or -not $ctx.dog){throw "Missing one core FTMO symbol: $ctxRaw"}
Write-Host ("Symbols: {0}, {1}, {2}" -f $ctx.btc,$ctx.eth,$ctx.dog)

Step "2/8 Resolve live MT5 data folder"
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
if($cands.Count -eq 0){throw "No data folder maps to FTMO install."}
$dataPath=$cands[0]

Step "3/8 Prepare isolated portable FTMO clone"
$Portable="D:\MT5_Backtests\Terminals\FTMO_D032_EXACT_$Stamp"
Robo (Split-Path $live.ExecutablePath -Parent) $Portable @("/XD","MQL5","bases","config","logs","tester","profiles")
Robo (Join-Path $dataPath "config") (Join-Path $Portable "config") @("/MIR")
$sourceBases=Join-Path $dataPath "bases"
if(Test-Path $sourceBases){Robo $sourceBases (Join-Path $Portable "bases") @("/XD","history","ticks")}
Set-Content (Join-Path $Portable "origin.txt") $Portable -Encoding ASCII
$ExpertDir=Join-Path $Portable "MQL5\Experts\GuardianResearch\Backtests"
New-Item -ItemType Directory -Force -Path $ExpertDir | Out-Null

Step "4/8 Compile EXACT recovered scanner"
if(-not (Test-Path $SourceEa)){throw "Missing exact source $SourceEa"}
$EaBase="D032_C1_CONFIRM_DojiStar_H1_v1_00"
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
  if((Get-Date)-gt $deadline){throw "Compile timeout. "+(Tail $CompileLog 500)}
  Start-Sleep -Milliseconds 500
}
if((Tail $CompileLog 1000) -match '(?i)([1-9][0-9]*)\s+error'){throw "Compile errors: "+(Tail $CompileLog 1000)}
$srcHash=(Get-FileHash $Mq5 -Algorithm SHA256).Hash
Write-Host ("Exact source SHA256: "+$srcHash)

Step "5/8 Run exact scanner on BTC / ETH / DOG"
$symbols=@($ctx.btc,$ctx.eth,$ctx.dog)
foreach($sym in $symbols){
  Write-Host ""
  Write-Host ("--- "+$sym+" ---") -ForegroundColor Yellow
  $baseOut=Join-Path $Common ("GuardianResearch\SETUP_SCANS\D032_C1_CONFIRM_DojiStar_H1\"+$sym)
  $before=@()
  if(Test-Path $baseOut){$before=@(Get-ChildItem $baseOut -Directory | ForEach-Object {$_.FullName})}

  $Ini=Join-Path $Tmp ("tester_"+$sym+".ini")
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
Symbol=$sym
Period=M1
Model=1
ExecutionMode=0
Optimization=0
FromDate=2018.07.01
ToDate=2024.01.01
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
  if(-not $proc.WaitForExit(7200000)){
    try{Stop-Process $proc.Id -Force}catch{}
    throw "Tester timeout for $sym"
  }
  Start-Sleep -Seconds 2

  if(-not (Test-Path $baseOut)){throw "No output folder created for $sym"}
  $after=@(Get-ChildItem $baseOut -Directory | Sort-Object LastWriteTime -Descending)
  $new=@($after | Where-Object {$before -notcontains $_.FullName})
  $picked=if($new.Count -gt 0){$new[0]}else{$after[0]}
  if(-not $picked){throw "Cannot resolve output run for $sym"}
  $dest=Join-Path $Runs $sym
  Copy-Item $picked.FullName $dest -Recurse -Force
  Copy-Item $Ini (Join-Path $dest "tester.ini") -Force
  Write-Host ("Collected: "+$picked.FullName) -ForegroundColor Green
}

Step "6/8 Analyze canonical clean parity"
& py -3 $Analyzer --root $Runs --out $Analysis 2>&1 | Tee-Object -FilePath (Join-Path $Work "ANALYSIS.log")
if($LASTEXITCODE -ne 0){throw "Analyzer failed."}

Step "7/8 Write run info"
[ordered]@{
  run_id=$RunId
  ftmo_login=$ctx.login
  ftmo_server=$ctx.server
  symbols=$symbols
  from="2018.07.01"
  to="2024.01.01"
  model="1 minute OHLC"
  exact_source="research/ea/D032_C1_CONFIRM_DojiStar_H1_v1_00.mq5"
  exact_source_sha256=$srcHash
  signal_logic_modified=$false
  protected_2026_accessed=$false
} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Work "RUN_INFO.json") -Encoding UTF8
Copy-Item $CompileLog (Join-Path $Work "compile.log") -Force -ErrorAction SilentlyContinue

Step "8/8 Zip"
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Work\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
Write-Host ("ZIP: "+$Zip) -ForegroundColor Green
try{Remove-Item $Portable -Recurse -Force -ErrorAction SilentlyContinue}catch{}
