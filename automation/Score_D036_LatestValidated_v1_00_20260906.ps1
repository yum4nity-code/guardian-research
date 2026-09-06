param(
    [ValidateSet('DEV_2024_2025','CONFIRM_2026_H1','SMOKE_MAR2025')]
    [string]$Stage='DEV_2024_2025',
    [string]$RepoRoot='D:\MT5_Backtests\guardian-research',
    [string]$ResultsRoot='D:\MT5_Backtests\guardian-backtest-autosync-results'
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$ExpectedSymbols=@('BTCUSD','ETHUSD','EURUSD','GBPUSD','USDJPY','XAUUSD')
$Scorer=Join-Path $RepoRoot 'research\analysis\analyze_d036_donchian_v0_v1_01.py'
$Inbox=Join-Path $ResultsRoot 'backtests\inbox'
$ReportDir=Join-Path $RepoRoot 'reports\research'

if(-not(Test-Path -LiteralPath $Scorer)){throw "Scorer introuvable: $Scorer"}
if(-not(Test-Path -LiteralPath $Inbox)){throw "Inbox AutoSync introuvable: $Inbox"}
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

function Read-FinalStats([string]$Path){
    $rows=@(Import-Csv -LiteralPath $Path -Delimiter ';')
    if($rows.Count -eq 0){return $null}
    $final=@($rows | Where-Object { $_.status -in @('FINAL','FINAL_INVALID_PNL_CALC') } | Select-Object -Last 1)
    if($final.Count -eq 0){return $null}
    return $final[0]
}

function Normalize-Symbol([string]$s){
    foreach($x in $ExpectedSymbols){if($s -like "*$x*"){return $x}}
    return $s
}

function Test-Integrity($st){
    if($null -eq $st){return $false}
    if($st.status -ne 'FINAL'){return $false}
    if($st.run_stage -ne $Stage){return $false}
    if($st.timeframe -ne 'PERIOD_H1'){return $false}

    foreach($name in @('trades_opened','trades_closed','csv_trade_rows','invalid_risk')){
        if(-not($st.PSObject.Properties.Name -contains $name)){return $false}
    }

    if([int64]$st.trades_opened -ne [int64]$st.trades_closed){return $false}
    if([int64]$st.trades_closed -ne [int64]$st.csv_trade_rows){return $false}
    if([int64]$st.invalid_risk -ne 0){return $false}

    if($st.PSObject.Properties.Name -contains 'pnl_calc_failures'){
        if([int64]$st.pnl_calc_failures -ne 0){return $false}
    }
    return $true
}

$selected=@()
foreach($symbol in $ExpectedSymbols){
    $dirs=@(Get-ChildItem -LiteralPath $Inbox -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^\d{8}_\d{6}_D036_' -and $_.Name -match [regex]::Escape($symbol) } |
        Sort-Object Name -Descending)

    $pick=$null
    foreach($d in $dirs){
        $stats=@(Get-ChildItem -LiteralPath $d.FullName -File -Filter "D036_V*_${Stage}_${symbol}_STATS.csv" -ErrorAction SilentlyContinue | Sort-Object Name -Descending)
        foreach($sf in $stats){
            $st=Read-FinalStats $sf.FullName
            if(-not(Test-Integrity $st)){continue}
            if((Normalize-Symbol $st.symbol) -ne $symbol){continue}

            $tradeName=$st.trades_name
            if([string]::IsNullOrWhiteSpace($tradeName)){
                $tradeName=$sf.Name -replace '_STATS\.csv$','_TRADES.csv'
            }
            $tf=Join-Path $d.FullName $tradeName
            if(-not(Test-Path -LiteralPath $tf)){continue}

            $pick=[pscustomobject]@{
                symbol=$symbol
                run_dir=$d.FullName
                stats=$sf.FullName
                trades=$tf
                source_name=$st.source_name
                source_version=$st.source_version
                opened=[int64]$st.trades_opened
                closed=[int64]$st.trades_closed
                rows=[int64]$st.csv_trade_rows
                pnl_fallbacks=if($st.PSObject.Properties.Name -contains 'pnl_fallbacks'){[int64]$st.pnl_fallbacks}else{0}
                pnl_calc_failures=if($st.PSObject.Properties.Name -contains 'pnl_calc_failures'){[int64]$st.pnl_calc_failures}else{0}
            }
            break
        }
        if($null -ne $pick){break}
    }
    if($null -eq $pick){throw "Aucun run D036 valide trouvé pour $symbol / $Stage"}
    $selected += $pick
}

Write-Host "`n=== D036 SELECTED VALID RUNS | $Stage ==="
$selected | Format-Table symbol,source_version,opened,closed,rows,pnl_fallbacks,pnl_calc_failures -AutoSize

$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$base="D036_${Stage}_LATEST_VALIDATED_SCORE_$stamp"
$jsonOut=Join-Path $ReportDir ($base+'.json')
$mdOut=Join-Path $ReportDir ($base+'.md')

$args=@($Scorer,'--stage',$Stage,'--out',$jsonOut)
foreach($x in $selected){$args += @('--input',$x.trades)}

$raw=& python @args
if($LASTEXITCODE -ne 0){throw "Scorer D036 a échoué (exit=$LASTEXITCODE)"}
if(-not(Test-Path -LiteralPath $jsonOut)){throw "Rapport JSON non créé: $jsonOut"}

$r=Get-Content -LiteralPath $jsonOut -Raw | ConvertFrom-Json

$lines=@()
$lines += "# D036 $Stage — latest validated score"
$lines += ""
$lines += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += ""
$lines += "## Verdict"
$lines += ""
$lines += "**$($r.verdict)**"
$lines += ""
$lines += "## Aggregate"
$lines += ""
$lines += "- N: $($r.aggregate.n)"
$lines += "- Total net R: $([math]::Round([double]$r.aggregate.sum,6))"
$lines += "- Mean net R: $([math]::Round([double]$r.aggregate.mean,6))"
$lines += "- Median net R: $([math]::Round([double]$r.aggregate.median,6))"
$lines += "- PF: $([math]::Round([double]$r.aggregate.pf,6))"
$lines += "- Win rate: $([math]::Round(100*[double]$r.aggregate.win_rate,2))%"
$lines += "- Stress 1.5x commission total R: $([math]::Round([double]$r.stress_1p5_commission.sum,6))"
$lines += "- Max losing streak: $($r.max_losing_streak)"
$lines += "- Positive-symbol concentration: $([math]::Round(100*[double]$r.positive_symbol_concentration,2))%"
$lines += ""
$lines += "## Selected runs"
$lines += ""
foreach($x in $selected){
    $lines += "- $($x.symbol): v$($x.source_version), opened=$($x.opened), closed=$($x.closed), rows=$($x.rows), fallbacks=$($x.pnl_fallbacks), pnl_failures=$($x.pnl_calc_failures)"
}
$lines += ""
$lines += "## Per symbol"
$lines += ""
foreach($s in $ExpectedSymbols){
    $z=$r.per_symbol.$s
    $lines += "- $s: N=$($z.n), total=$([math]::Round([double]$z.sum,6))R, mean=$([math]::Round([double]$z.mean,6))R, PF=$([math]::Round([double]$z.pf,6)), WR=$([math]::Round(100*[double]$z.win_rate,2))%"
}
$lines += ""
$lines += "## Gates"
$lines += ""
foreach($p in $r.gates.PSObject.Properties){$lines += "- $($p.Name): $($p.Value)"}

Set-Content -LiteralPath $mdOut -Value $lines -Encoding UTF8

Write-Host "`n=== D036 SCORE ==="
Write-Host "VERDICT: $($r.verdict)"
Write-Host "N=$($r.aggregate.n) | total=$([math]::Round([double]$r.aggregate.sum,4))R | mean=$([math]::Round([double]$r.aggregate.mean,4))R | PF=$([math]::Round([double]$r.aggregate.pf,4)) | WR=$([math]::Round(100*[double]$r.aggregate.win_rate,2))%"
Write-Host "Stress 1.5x total=$([math]::Round([double]$r.stress_1p5_commission.sum,4))R | concentration=$([math]::Round(100*[double]$r.positive_symbol_concentration,2))% | losing streak=$($r.max_losing_streak)"
Write-Host "JSON: $jsonOut"
Write-Host "MD:   $mdOut"
