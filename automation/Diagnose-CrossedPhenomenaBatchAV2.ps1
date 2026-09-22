param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Base=Join-Path $Root "Research\Autonomous\guardian_crossed_batch_a_v2"
if(!(Test-Path $Base)){ throw "No Batch A V2 directory" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$Csv=Join-Path $Run.FullName "DISCOVERY_2013_2016_ALL.csv"
if(!(Test-Path $Csv)){ throw "Missing $Csv" }
$D=Import-Csv $Csv
Write-Host "=== BATCH A V2 INVALID-TEST DIAGNOSTIC ==="
Write-Host "RUN:" $Run.FullName
Write-Host "ROWS:" $D.Count
Write-Host ""
$D | Group-Object lineage | ForEach-Object {
  $g=$_.Group
  $n=@($g|ForEach-Object{[double]$_.n})
  $c=@($g|ForEach-Object{[double]$_.clusters})
  $coef=@($g|Where-Object{$_.coef -notin @("","nan","NaN")}).Count
  $t=@($g|Where-Object{$_.t -notin @("","nan","NaN")}).Count
  $p=@($g|Where-Object{$_.p_two -notin @("","nan","NaN")}).Count
  [pscustomobject]@{
    lineage=$_.Name;tests=$g.Count
    n_min=($n|Measure-Object -Minimum).Minimum
    n_max=($n|Measure-Object -Maximum).Maximum
    clusters_min=($c|Measure-Object -Minimum).Minimum
    clusters_max=($c|Measure-Object -Maximum).Maximum
    coef_finite=$coef;t_finite=$t;p_finite=$p
  }
}|Format-Table -AutoSize

Write-Host ""
Write-Host "=== ALL 66 TEST ROWS ==="
$D | Select-Object lineage,variant,horizon_min,n,clusters,coef_bp,t,p_two,valid,bh_q,bh_pass | Format-Table -AutoSize

Write-Host ""
Write-Host "=== FAILURE COUNTS ==="
[pscustomobject]@{
  n_lt_120=@($D|Where-Object{[double]$_.n -lt 120}).Count
  clusters_lt_80=@($D|Where-Object{[double]$_.clusters -lt 80}).Count
  p_missing=@($D|Where-Object{$_.p_two -in @("","nan","NaN")}).Count
  coef_missing=@($D|Where-Object{$_.coef -in @("","nan","NaN")}).Count
}|Format-List
