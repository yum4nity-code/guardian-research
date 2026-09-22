param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Base=Join-Path $Root "Research\Autonomous\guardian_crossed_batch_a_discovery"
if(!(Test-Path $Base)){ throw "No Batch A directory" }
$Run=Get-ChildItem $Base -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(!$Run){ throw "No Batch A run" }
$Csv=Join-Path $Run.FullName "DISCOVERY_2010_2012_ALL.csv"
if(!(Test-Path $Csv)){ throw "Missing $Csv" }
$D=Import-Csv $Csv
Write-Host "=== BATCH A INVALID-TEST DIAGNOSTIC ==="
Write-Host "RUN:" $Run.FullName
Write-Host "ROWS:" $D.Count
Write-Host ""
$D | Group-Object lineage | ForEach-Object {
  $g=$_.Group
  $nVals=@($g | ForEach-Object {[double]$_.discovery_n})
  $cVals=@($g | ForEach-Object {[double]$_.discovery_clusters})
  $coefFinite=@($g | Where-Object { $_.discovery_coef -notin @("","nan","NaN") }).Count
  $tFinite=@($g | Where-Object { $_.discovery_t -notin @("","nan","NaN") }).Count
  $pFinite=@($g | Where-Object { $_.discovery_p_two -notin @("","nan","NaN") }).Count
  [pscustomobject]@{
    lineage=$_.Name
    tests=$g.Count
    n_min=($nVals | Measure-Object -Minimum).Minimum
    n_max=($nVals | Measure-Object -Maximum).Maximum
    clusters_min=($cVals | Measure-Object -Minimum).Minimum
    clusters_max=($cVals | Measure-Object -Maximum).Maximum
    coef_finite=$coefFinite
    t_finite=$tFinite
    p_finite=$pFinite
  }
} | Format-Table -AutoSize

Write-Host ""
Write-Host "=== FIRST 20 TEST ROWS ==="
$D | Select-Object -First 20 lineage,variant,horizon_min,discovery_n,discovery_clusters,discovery_coef_bp,discovery_t,discovery_p_two,discovery_valid | Format-Table -AutoSize

Write-Host ""
Write-Host "=== MAX N / CLUSTERS BY LINEAGE ==="
$D | Sort-Object {[double]$_.discovery_n} -Descending | Select-Object -First 12 lineage,variant,horizon_min,discovery_n,discovery_clusters,discovery_coef_bp,discovery_t,discovery_p_two | Format-Table -AutoSize
