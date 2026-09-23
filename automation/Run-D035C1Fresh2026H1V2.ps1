param(
  [string]$Root="D:\MT5_Backtests"
)
$ErrorActionPreference="Stop"

$Repo=Join-Path $Root "guardian-research"
$Py=Join-Path $Repo "scripts\run_d035_c1_fresh_2026h1_v2.py"
$Auth=Join-Path $Repo "research\campaigns\D035_C1_2026H1_HUMAN_AUTHORIZATION_2026_09_23.json"
if(!(Test-Path $Py)){ throw "Missing $Py" }
if(!(Test-Path $Auth)){ throw "Missing human authorization $Auth" }

$authObj=Get-Content $Auth -Raw | ConvertFrom-Json
if(-not $authObj.authorized_by_owner){ throw "Owner authorization is not true." }

Write-Host "=== D035-C1 FRESH 2026-H1 CONFIRMATION ==="
Write-Host "LOCKED: XLMUSD SHORT, BTC+ETH <=5m, second shock, +15m primary."
Write-Host "NO JUL-DEC 2026. NO OTHER TARGETS. NO RETUNING."

# Find a full local D035 analyzer, never use the repo continuity marker.
$searchRoots=@(
  $Root,
  (Join-Path $HOME "Downloads"),
  (Join-Path $HOME "Desktop")
) | Where-Object { Test-Path $_ }

$baseAnalyzer=$null
foreach($sr in $searchRoots){
  $cands=Get-ChildItem $sr -Recurse -File -Filter "D035_Binance_Deleveraging_LeadLag_v1_0*.py" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending
  foreach($c in $cands){
    $txt=Get-Content $c.FullName -Raw -ErrorAction SilentlyContinue
    if($null -ne $txt -and $txt.Contains("def load_metrics") -and $txt.Contains("def load_cfd_files") -and -not $txt.Contains("continuity marker only")){
      $baseAnalyzer=$c.FullName
      break
    }
  }
  if($baseAnalyzer){ break }
}
if(-not $baseAnalyzer){
  throw "Full local D035 analyzer not found. Need the previously delivered D035_Binance_Deleveraging_LeadLag_v1_00/v1_01.py (not the small repo continuity marker)."
}
Write-Host "Base analyzer: $baseAnalyzer"

# Find latest authorized MT5 exports. Exporter writes one file per current tester symbol.
$commonRoot=Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files\GuardianResearch\SETUP_SCANS\D035_CFD_M1_EXPORT"
$btc=Get-ChildItem (Join-Path $commonRoot "BTCUSD") -Recurse -File -Filter "D035_CFD_M1_BTCUSD.csv" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
$xlm=Get-ChildItem (Join-Path $commonRoot "XLMUSD") -Recurse -File -Filter "D035_CFD_M1_XLMUSD.csv" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1

if(-not $btc -or -not $xlm){
  Write-Host ""
  Write-Host "NEEDS_CFD_EXPORT"
  Write-Host "Run research\ea\D035_CFD_M1_Exporter_v1_01.mq5 in FundedNext MT5 Strategy Tester:"
  Write-Host "  1) BTCUSD, M1, Every tick, 2026-01-01 -> 2026-07-01"
  Write-Host "  2) XLMUSD, M1, Every tick, 2026-01-01 -> 2026-07-01"
  Write-Host "Then rerun this PowerShell command. The runner will find the files automatically."
  exit 2
}

$work=Join-Path $Root "Research\Autonomous\d035_c1_2026h1_v2"
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
