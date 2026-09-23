param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"

$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\run_d035_f1_ftmo_transport_2026h1_v1.py"
$Auth=Join-Path $Repo "research\campaigns\D035_F1_FTMO_2026H1_HUMAN_AUTHORIZATION_2026_09_23.json"
$Payload=Join-Path $Repo "research\analysis\D035_Binance_Deleveraging_LeadLag_v1_01.py.gz.b64"
$ExpectedAnalyzerSha="35E7579B25ABEBCDD32829168598F58CEA4C835C30B0E02D9CDEE882E4327168"

if(!(Test-Path $Py) -or !(Test-Path $Auth) -or !(Test-Path $Payload)){ throw "Missing D035-F1 support file." }
$authObj=Get-Content $Auth -Raw | ConvertFrom-Json
if(-not $authObj.authorized_by_owner){ throw "D035-F1 not authorized." }

Write-Host "=== D035-F1 FTMO TRANSPORT CONFIRMATION ==="
Write-Host "LOCKED: XLMUSD SHORT, BTC+ETH <=5m, second shock, +15m."
Write-Host "FTMO commission 0.0325% per side. NO OTHER TARGETS. NO RETUNING."

$work=Join-Path $Root "Research\Autonomous\d035_f1_ftmo_2026h1"
$support=Join-Path $work "support"
New-Item -ItemType Directory -Force -Path $support | Out-Null
$baseAnalyzer=Join-Path $support "D035_Binance_Deleveraging_LeadLag_v1_01_RECOVERED.py"

$encoded=(Get-Content $Payload -Raw).Trim()
$compressed=[Convert]::FromBase64String($encoded)
$inStream=New-Object System.IO.MemoryStream(,$compressed)
$gzip=New-Object System.IO.Compression.GZipStream($inStream,[System.IO.Compression.CompressionMode]::Decompress)
$outStream=[System.IO.File]::Create($baseAnalyzer)
try { $gzip.CopyTo($outStream) } finally { $outStream.Dispose(); $gzip.Dispose(); $inStream.Dispose() }
$actualSha=(Get-FileHash $baseAnalyzer -Algorithm SHA256).Hash.ToUpperInvariant()
if($actualSha -ne $ExpectedAnalyzerSha){ throw "D035 analyzer SHA mismatch." }

$commonRoot=Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files\GuardianResearch\SETUP_SCANS\D035_FTMO_CFD_M1_EXPORT"

function Get-Coverage([System.IO.FileInfo]$File){
  try {
    $head=Get-Content $File.FullName -TotalCount 2
    $first=$head | Select-Object -Last 1
    $last=Get-Content $File.FullName -Tail 1
    if(-not $first -or -not $last){ return $null }
    $a=$first -split ';'; $b=$last -split ';'
    if($a.Count -lt 21 -or $b.Count -lt 21){ return $null }
    $start=Get-Date -Year ([int]$a[13]) -Month ([int]$a[14]) -Day ([int]$a[15])
    $end=Get-Date -Year ([int]$b[13]) -Month ([int]$b[14]) -Day ([int]$b[15])
    $company=$a[19]; $server=$a[20]
    [pscustomobject]@{File=$File;Start=$start;End=$end;Company=$company;Server=$server;Covers=($start -le [datetime]"2026-01-07" -and $end -ge [datetime]"2026-06-25")}
  } catch { return $null }
}

function Find-FTMO([string]$Symbol){
  $dir=Join-Path $commonRoot $Symbol
  if(!(Test-Path $dir)){ return $null }
  $valid=@()
  foreach($f in Get-ChildItem $dir -Recurse -File -Filter "D035_CFD_M1_$Symbol.csv" -ErrorAction SilentlyContinue){
    $x=Get-Coverage $f
    if($null -ne $x -and $x.Covers -and (($x.Company+$x.Server).ToUpperInvariant().Contains("FTMO"))){ $valid += $x }
  }
  return $valid | Sort-Object { $_.File.LastWriteTime } -Descending | Select-Object -First 1
}

$btcCov=Find-FTMO "BTCUSD"
$xlmCov=Find-FTMO "XLMUSD"

if(-not $btcCov -or -not $xlmCov){
  Write-Host ""
  Write-Host "NEEDS_FTMO_EXPORT"
  Write-Host "Use research\ea\D035_FTMO_CFD_M1_Exporter_v1_00.mq5 in your FTMO MT5 Strategy Tester:"
  Write-Host "  Period: 2026-01-01 -> 2026-07-01"
  Write-Host "  Timeframe: M1"
  Write-Host "  Model: 1 minute OHLC"
  Write-Host "  1) BTCUSD"
  Write-Host "  2) XLMUSD"
  exit 2
}

Write-Host ("BTC FTMO coverage: {0:yyyy-MM-dd} -> {1:yyyy-MM-dd} | {2} | {3}" -f $btcCov.Start,$btcCov.End,$btcCov.Company,$btcCov.Server)
Write-Host ("XLM FTMO coverage: {0:yyyy-MM-dd} -> {1:yyyy-MM-dd} | {2} | {3}" -f $xlmCov.Start,$xlmCov.End,$xlmCov.Company,$xlmCov.Server)

$cfd=Join-Path $work "cfd_inputs"; $out=Join-Path $work "result"; $cache=Join-Path $Root "D035_binance_cache"
New-Item -ItemType Directory -Force -Path $cfd,$out,$cache | Out-Null
Get-ChildItem $cfd -File -ErrorAction SilentlyContinue | Remove-Item -Force
Copy-Item $btcCov.File.FullName (Join-Path $cfd "D035_CFD_M1_BTCUSD.csv") -Force
Copy-Item $xlmCov.File.FullName (Join-Path $cfd "D035_CFD_M1_XLMUSD.csv") -Force

py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "D035-F1 compile failed" }
py $Py --base-analyzer "$baseAnalyzer" --cfd-dir "$cfd" --cache-dir "$cache" --out-dir "$out"
if($LASTEXITCODE -ne 0){ throw "D035-F1 failed" }
