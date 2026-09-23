$ErrorActionPreference = "Stop"
$Root = "D:\MT5_Backtests\Research\ExecutionAudit"
$Repo = "D:\MT5_Backtests\guardian-research"
$Analyzer = Join-Path $Repo "tools\analyze_d032_exact_ftmo_parity_v1_01.py"

$Run = Get-ChildItem $Root -Directory -Filter "D032_EXACT_FTMO_*" |
       Sort-Object LastWriteTime -Descending |
       Select-Object -First 1
if(-not $Run){ throw "No existing D032_EXACT_FTMO_* run found." }

$Runs = Join-Path $Run.FullName "runs"
$Analysis = Join-Path $Run.FullName "analysis_v1_01"
$Log = Join-Path $Run.FullName "ANALYSIS_v1_01.log"
$Zip = Join-Path ([Environment]::GetFolderPath("Desktop")) ("GUARDIAN_D032_EXACT_FTMO_PARITY_ANALYZED_"+$Run.Name.Replace("D032_EXACT_FTMO_","")+".zip")
New-Item -ItemType Directory -Force -Path $Analysis | Out-Null

Write-Host ("Reusing completed MT5 run: "+$Run.FullName) -ForegroundColor Cyan
Write-Host "NO MT5 BACKTEST WILL BE RERUN." -ForegroundColor Yellow

$Old=$ErrorActionPreference
$ErrorActionPreference="Continue"
& py -3 $Analyzer --root $Runs --out $Analysis 2>&1 | Tee-Object -FilePath $Log
$Code=$LASTEXITCODE
$ErrorActionPreference=$Old
if($Code -ne 0){ throw "Analyzer failed; full traceback saved to $Log" }

if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$($Run.FullName)\*" -DestinationPath $Zip -CompressionLevel Optimal -Force
Write-Host ("ZIP: "+$Zip) -ForegroundColor Green
