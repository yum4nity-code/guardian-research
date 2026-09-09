@echo off
setlocal
title Guardian Research - Status
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p='D:\MT5_Backtests\Research\Autonomous\orchestrator_health.json';" ^
  "if(-not (Test-Path $p)){Write-Host '';Write-Host '🔴 STOPPE / INJOIGNABLE' -ForegroundColor Red;Write-Host 'Aucun heartbeat trouve.';Write-Host '';exit};" ^
  "try{$h=Get-Content -Raw $p ^| ConvertFrom-Json}catch{Write-Host '';Write-Host '🔴 STOPPE / ERREUR' -ForegroundColor Red;Write-Host 'Heartbeat illisible.';Write-Host '';exit};" ^
  "$t=[datetimeoffset]::Parse($h.updated_at_utc);$age=((Get-Date).ToUniversalTime()-$t.UtcDateTime).TotalSeconds;" ^
  "$job='';if($h.active_job){$job=$h.active_job.id+' r'+$h.active_job.revision}elseif($h.last_receipt){$job=Split-Path $h.last_receipt -Leaf};" ^
  "Write-Host '';" ^
  "if($h.status -eq 'RUNNING' -and $age -lt 180){Write-Host '🟢 CA BOSSE' -ForegroundColor Green}" ^
  "elseif($h.status -in @('WAITING','IDLE','PASS') -and $age -lt 180){Write-Host '🟠 EN ATTENTE / ENTRE DEUX JOBS' -ForegroundColor Yellow}" ^
  "elseif($h.status -in @('FAIL','TIMEOUT','BLOCKED','ORCHESTRATOR_ERROR')){Write-Host '🔴 BLOQUE / ERREUR' -ForegroundColor Red}" ^
  "elseif($age -ge 180){Write-Host '🔴 STOPPE ? HEARTBEAT TROP VIEUX' -ForegroundColor Red}" ^
  "else{Write-Host '🟠 ETAT A VERIFIER' -ForegroundColor Yellow};" ^
  "Write-Host ('Etat brut : '+$h.status);Write-Host ('Dernier signal : '+$t.ToLocalTime().ToString('dd/MM/yyyy HH:mm:ss'));Write-Host ('Age : '+[math]::Round($age)+' s');if($job){Write-Host ('Job : '+$job)};Write-Host '';"
echo.
echo Si c'est ROUGE, copie-moi simplement ce qui est affiche ici.
echo.
pause
