param([string]$Root='D:\MT5_Backtests',[int]$RefreshSeconds=30)
$ErrorActionPreference='SilentlyContinue'
function Latest($p,$filter='*'){if(Test-Path $p){Get-ChildItem $p -File -Filter $filter|Sort-Object LastWriteTime -Descending|Select-Object -First 1}}
while($true){
 Clear-Host
 $now=Get-Date
 Write-Host ('GUARDIAN — RECHERCHE EA     '+$now.ToString('yyyy-MM-dd HH:mm:ss'))
 Write-Host ('='*82)
 Write-Host 'Objectif : trouver au moins un candidat EA robuste | FTMO prioritaire | FundedNext secondaire'
 Write-Host '2026 : PROTEGE — jamais ouvert avant le gate final canonique'
 Write-Host ''
 $procs=Get-CimInstance Win32_Process|Where-Object {$_.CommandLine -match 'guardian|research|r1[0-9]|literature|replication' -and $_.Name -match 'python|powershell|pwsh'}
 Write-Host 'PROCESSUS ACTIFS'
 if($procs){foreach($p in $procs){$gp=Get-Process -Id $p.ProcessId; Write-Host (' PID {0} | CPU {1:N1}s | RAM {2:N0} MB | {3}' -f $p.ProcessId,$gp.CPU,($gp.WorkingSet64/1MB),($p.CommandLine.Substring(0,[Math]::Min(130,$p.CommandLine.Length))))}}else{Write-Host ' aucun moteur detecte'}
 $dirs=@(
  (Join-Path $Root 'Research\Autonomous\progress'),
  (Join-Path $Root 'research\autonomous\progress'),
  (Join-Path $Root 'Research\Autonomous\reports'),
  (Join-Path $Root 'research\autonomous\reports')
 )|Select-Object -Unique
 Write-Host ''; Write-Host 'DERNIER ETAT'
 foreach($d in $dirs){$f=Latest $d '*.json'; if($f){Write-Host (' '+$f.FullName+' | '+$f.LastWriteTime.ToString('HH:mm:ss')); try{$j=Get-Content $f.FullName -Raw|ConvertFrom-Json; foreach($k in @('family','stage','status','completed','total','tested','discovery_candidates','confirmation_candidates','economic_survivors','pre_oos_survivors','message')){if($null-ne $j.$k){Write-Host ('   {0,-25} {1}' -f $k,$j.$k)}}}catch{}}}
 Write-Host ''; Write-Host 'FICHIERS RECENTS'
 Get-ChildItem $Root -File -Recurse -ErrorAction SilentlyContinue|Where-Object {$_.LastWriteTime -gt $now.AddMinutes(-30) -and $_.FullName -match 'Research|research'}|Sort-Object LastWriteTime -Descending|Select-Object -First 10|ForEach-Object{Write-Host (' '+$_.LastWriteTime.ToString('HH:mm:ss')+'  '+$_.FullName)}
 Write-Host ''; Write-Host ('Rafraichissement toutes les '+$RefreshSeconds+' s — Ctrl+C pour fermer uniquement cet affichage')
 Start-Sleep -Seconds $RefreshSeconds
}
