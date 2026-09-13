param(
 [string]$Root='D:\MT5_Backtests',
 [int]$RefreshSeconds=15,
 [int]$StallMinutes=10
)
$ErrorActionPreference='SilentlyContinue'
$progressDir=Join-Path $Root 'Research\Autonomous\progress'
$reportsDir=Join-Path $Root 'Research\Autonomous\reports'
$logsDir=Join-Path $Root 'Research\Autonomous\logs'
function Latest($p,$f='*'){if(Test-Path -LiteralPath $p){Get-ChildItem -LiteralPath $p -File -Filter $f|Sort-Object LastWriteTime -Descending|Select-Object -First 1}}
function Val($o,$n,$d='-'){if($null -ne $o -and $null -ne $o.$n){return [string]$o.$n};$d}
function Short($s,$n=125){if([string]::IsNullOrWhiteSpace($s)){return ''};$s=($s-replace '\s+',' ').Trim();if($s.Length-le$n){$s}else{$s.Substring(0,$n-3)+'...'}}
while($true){
 Clear-Host;$now=Get-Date
 $procs=Get-CimInstance Win32_Process|?{$_.Name-match 'python|powershell|pwsh' -and $_.CommandLine-match 'guardian|research|autonomous|r1[0-9]'}
 $pf=Latest $progressDir '*.json';$j=$null;if($pf){try{$j=Get-Content -LiteralPath $pf.FullName -Raw|ConvertFrom-Json}catch{}}
 $lf=Latest $logsDir '*.log';$rf=Latest $reportsDir '*'
 $age=$null;if($pf){$age=($now-$pf.LastWriteTime).TotalMinutes}
 $raw=((Val $j 'status')+' '+(Val $j 'stage')+' '+(Val $j 'message')).ToLower()
 if($raw-match 'error|exception|infra|failed'){ $state='INFRA ERROR';$c='Red' }
 elseif($raw-match 'scientific.fail|scientific_fail'){ $state='SCIENTIFIC FAIL';$c='Yellow' }
 elseif($raw-match 'complete|completed|done'){ $state='COMPLETE';$c='Green' }
 elseif($procs -and $age -ne $null -and $age -gt $StallMinutes){$state='STALLED?';$c='Yellow'}
 elseif($procs){$state='RUNNING';$c='Green'}
 else{$state='IDLE / UNKNOWN';$c='DarkYellow'}
 Write-Host 'GUARDIAN MONITOR V1' -ForegroundColor Cyan
 Write-Host ('='*78)
 Write-Host ('STATUS : '+$state) -ForegroundColor $c
 Write-Host ('Time   : '+$now.ToString('yyyy-MM-dd HH:mm:ss')+'    refresh '+$RefreshSeconds+'s')
 Write-Host ('Family : '+(Val $j 'family')+'    Stage: '+(Val $j 'stage'))
 if($pf){Write-Host ('Heartbeat: '+$pf.LastWriteTime.ToString('HH:mm:ss')+'  age '+([math]::Round($age,1))+' min  '+$pf.Name)}
 Write-Host ''
 Write-Host 'ENGINE' -ForegroundColor Cyan
 if($procs){foreach($p in $procs){$gp=Get-Process -Id $p.ProcessId;Write-Host ('PID {0,-7} CPU {1,8}s RAM {2,7}MB  {3}' -f $p.ProcessId,([math]::Round($gp.CPU,1)),([math]::Round($gp.WorkingSet64/1MB)),(Short $p.CommandLine))}}else{Write-Host 'No Guardian research process detected.'}
 Write-Host ''
 Write-Host 'FUNNEL' -ForegroundColor Cyan
 $pairs=@(@('Tested','tested'),@('Discovery','discovery_candidates'),@('Confirmation','confirmation_candidates'),@('Economic','economic_candidates'),@('Pre-OOS','pre_oos_survivors'))
 foreach($x in $pairs){Write-Host ('{0,-16} {1}' -f $x[0],(Val $j $x[1]))}
 $done=Val $j 'completed' ''; $tot=Val $j 'total' ''
 if($done -ne '' -and $tot -ne '' -and [double]$tot -gt 0){$pct=[math]::Round(100*[double]$done/[double]$tot,1);Write-Host ('Progress         {0}/{1}  ({2}%)' -f $done,$tot,$pct)}
 Write-Host ''
 Write-Host 'LATEST' -ForegroundColor Cyan
 if($lf){Write-Host ('Log    : '+$lf.Name+' @ '+$lf.LastWriteTime.ToString('HH:mm:ss'))}else{Write-Host 'Log    : -'}
 if($rf){Write-Host ('Report : '+$rf.Name+' @ '+$rf.LastWriteTime.ToString('HH:mm:ss'))}else{Write-Host 'Report : -'}
 $msg=Val $j 'message' '';if($msg){Write-Host ('Message: '+(Short $msg 150))}
 Write-Host ''
 Write-Host 'LAST LOG LINES' -ForegroundColor Cyan
 if($lf){Get-Content -LiteralPath $lf.FullName -Tail 8}
 Write-Host ''
 Write-Host 'READ ONLY - never starts/stops/modifies Guardian - Ctrl+C to quit' -ForegroundColor DarkGray
 Start-Sleep -Seconds $RefreshSeconds
}
