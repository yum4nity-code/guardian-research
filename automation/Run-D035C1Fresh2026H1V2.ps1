param(
  [string]$Root="D:\MT5_Backtests"
)
$ErrorActionPreference="Stop"

$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\run_d035_c1_fresh_2026h1_v2.py"
$Auth=Join-Path $Repo "research\campaigns\D035_C1_2026H1_HUMAN_AUTHORIZATION_2026_09_23.json"
$Payload=Join-Path $Repo "research\analysis\D035_Binance_Deleveraging_LeadLag_v1_01.py.gz.b64"
$ExpectedAnalyzerSha="35E7579B25ABEBCDD32829168598F58CEA4C835C30B0E02D9CDEE882E4327168"

if(!(Test-Path $Py)){ throw "Missing $Py" }
if(!(Test-Path $Auth)){ throw "Missing human authorization $Auth" }
if(!(Test-Path $Payload)){ throw "Missing recovered frozen analyzer payload $Payload" }

$authObj=Get-Content $Auth -Raw | ConvertFrom-Json
if(-not $authObj.authorized_by_owner){ throw "Owner authorization is not true." }

Write-Host "=== D035-C1 FRESH 2026-H1 CONFIRMATION ==="
Write-Host "LOCKED: XLMUSD SHORT, BTC+ETH <=5m, second shock, +15m primary."
Write-Host "NO JUL-DEC 2026. NO OTHER TARGETS. NO RETUNING."

# Restore the exact D035 v1.01 analyzer originally delivered on 2026-09-05.
# The repository previously held only a continuity marker, so the exact source
# is now archived losslessly as gzip+base64 and hash-checked before use.
$work=Join-Path $Root "Research\Autonomous\d035_c1_2026h1_v2"
$support=Join-Path $work "support"
New-Item -ItemType Directory -Force -Path $support | Out-Null
$baseAnalyzer=Join-Path $support "D035_Binance_Deleveraging_LeadLag_v1_01_RECOVERED.py"

$encoded=(Get-Content $Payload -Raw).Trim()
$compressed=[Convert]::FromBase64String($encoded)
$inStream=New-Object System.IO.MemoryStream(,$compressed)
$gzip=New-Object System.IO.Compression.GZipStream($inStream,[System.IO.Compression.CompressionMode]::Decompress)
$outStream=[System.IO.File]::Create($baseAnalyzer)
try {
  $gzip.CopyTo($outStream)
} finally {
  $outStream.Dispose()
  $gzip.Dispose()
  $inStream.Dispose()
}

$actualSha=(Get-FileHash $baseAnalyzer -Algorithm SHA256).Hash.ToUpperInvariant()
if($actualSha -ne $ExpectedAnalyzerSha){
  throw "Recovered D035 analyzer SHA mismatch: $actualSha expected $ExpectedAnalyzerSha"
}
$txt=Get-Content $baseAnalyzer -Raw
if(-not $txt.Contains("def load_metrics") -or -not $txt.Contains("def load_cfd_files")){
  throw "Recovered D035 analyzer API sanity check failed."
}
py -m py_compile $baseAnalyzer
if($LASTEXITCODE -ne 0){ throw "Recovered D035 analyzer compile failed" }
Write-Host "Base analyzer recovered and verified: $baseAnalyzer"
Write-Host "SHA256: $actualSha"

# Find authorized MT5 exports by ACTUAL COVERAGE, never by file mtime alone.
$commonRoot=Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files\GuardianResearch\SETUP_SCANS\D035_CFD_M1_EXPORT"

function Get-D035CsvCoverage([System.IO.FileInfo]$File){
  try {
    $firstData = Get-Content $File.FullName -TotalCount 2 | Select-Object -Last 1
    $lastData = Get-Content $File.FullName -Tail 1
    if(-not $firstData -or -not $lastData){ return $null }

    $a=$firstData -split ';'
    $b=$lastData -split ';'
    if($a.Count -lt 19 -or $b.Count -lt 19){ return $null }

    # Frozen exporter fields: server_year/month/day at indices 13/14/15.
    $start=Get-Date -Year ([int]$a[13]) -Month ([int]$a[14]) -Day ([int]$a[15]) -Hour 0 -Minute 0 -Second 0
    $end=Get-Date -Year ([int]$b[13]) -Month ([int]$b[14]) -Day ([int]$b[15]) -Hour 0 -Minute 0 -Second 0

    [pscustomobject]@{
      File=$File
      Start=$start
      End=$end
      CoversH1=($start -le [datetime]"2026-01-07" -and $end -ge [datetime]"2026-06-25")
    }
  } catch {
    return $null
  }
}

function Find-D035H1Export([string]$Symbol){
  $dir=Join-Path $commonRoot $Symbol
  if(!(Test-Path $dir)){ return $null }

  $all=Get-ChildItem $dir -Recurse -File -Filter "D035_CFD_M1_$Symbol.csv" -ErrorAction SilentlyContinue
  $cov=@()
  foreach($f in $all){
    $x=Get-D035CsvCoverage $f
    if($null -ne $x){ $cov += $x }
  }

  $valid=$cov | Where-Object { $_.CoversH1 } | Sort-Object { $_.File.LastWriteTime } -Descending
  if($valid){ return ($valid | Select-Object -First 1) }

  if($cov){
    Write-Host ""
    Write-Host "$Symbol exports found but NONE covers 2026-H1:"
    $cov | Sort-Object Start | ForEach-Object {
      Write-Host ("  {0}  coverage={1:yyyy-MM-dd} -> {2:yyyy-MM-dd}" -f $_.File.FullName,$_.Start,$_.End)
    }
  }
  return $null
}

$btcCov=Find-D035H1Export "BTCUSD"
$xlmCov=Find-D035H1Export "XLMUSD"
$btc=if($btcCov){$btcCov.File}else{$null}
$xlm=if($xlmCov){$xlmCov.File}else{$null}

if(-not $btc -or -not $xlm){
  Write-Host ""
  Write-Host "NEEDS_CFD_EXPORT"
  Write-Host "The old 2023-2025 exports are intentionally rejected."
  Write-Host "Run research\ea\D035_CFD_M1_Exporter_v1_01.mq5 in FundedNext MT5 Strategy Tester:"
  Write-Host "  Model: 1 minute OHLC (frozen D035 export protocol)"
  Write-Host "  Period: 2026-01-01 -> 2026-07-01"
  Write-Host "  1) BTCUSD, M1"
  Write-Host "  2) XLMUSD, M1"
  Write-Host "Then rerun this exact PowerShell command."
  exit 2
}

Write-Host ("BTC coverage: {0:yyyy-MM-dd} -> {1:yyyy-MM-dd}" -f $btcCov.Start,$btcCov.End)
Write-Host ("XLM coverage: {0:yyyy-MM-dd} -> {1:yyyy-MM-dd}" -f $xlmCov.Start,$xlmCov.End)

$cfd=Join-Path $work "cfd_inputs"
$out=Join-Path $work "result"
$cache=Join-Path $Root "D035_binance_cache"
New-Item -ItemType Directory -Force -Path $cfd,$out,$cache | Out-Null

# Clean input directory so no protected extra target can be read accidentally.
Get-ChildItem $cfd -File -ErrorAction SilentlyContinue | Remove-Item -Force
Copy-Item $btc.FullName (Join-Path $cfd "D035_CFD_M1_BTCUSD.csv") -Force
Copy-Item $xlm.FullName (Join-Path $cfd "D035_CFD_M1_XLMUSD.csv") -Force

Write-Host "BTC export: $($btc.FullName)"
Write-Host "XLM export: $($xlm.FullName)"

py -m py_compile $Py
if($LASTEXITCODE -ne 0){ throw "C1 script compile failed" }

py $Py --base-analyzer "$baseAnalyzer" --cfd-dir "$cfd" --cache-dir "$cache" --out-dir "$out"
if($LASTEXITCODE -ne 0){ throw "D035-C1 fresh confirmation failed" }
