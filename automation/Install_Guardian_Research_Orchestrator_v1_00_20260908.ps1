$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$TaskName = "GuardianResearchOrchestratorV1"
$Root = "D:\MT5_Backtests\Research\Autonomous"
$Deploy = "D:\MT5_Backtests\guardian-autonomous-main"
$Remote = "https://github.com/yum4nity-code/guardian-research.git"
$RuntimeDir = Join-Path $Root "runtime"
$RuntimeScript = Join-Path $RuntimeDir "guardian_research_orchestrator_v1_00.py"
$SourceScript = Join-Path $PSScriptRoot "..\research\autonomous\guardian_research_orchestrator_v1_00.py"
$TestScript = Join-Path $PSScriptRoot "..\research\autonomous\test_guardian_research_orchestrator_v1_00.py"

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return [pscustomobject]@{ Exe=$py.Source; Prefix=@("-3") } }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return [pscustomobject]@{ Exe=$python.Source; Prefix=@() } }
    throw "Python 3 not found."
}

Write-Host "=== GUARDIAN AUTONOMOUS RESEARCH ORCHESTRATOR v1.00 ===" -ForegroundColor Cyan
foreach ($p in @($SourceScript,$TestScript)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing installer dependency: $p" }
}

$py = Find-Python
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

Write-Host "Running orchestrator tests..."
& $py.Exe @($py.Prefix) $TestScript | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Orchestrator tests failed; refusing installation." }

Write-Host "Compiling orchestrator..."
& $py.Exe @($py.Prefix) -m py_compile $SourceScript
if ($LASTEXITCODE -ne 0) { throw "Orchestrator Python compile failed." }

Copy-Item -LiteralPath $SourceScript -Destination $RuntimeScript -Force
$srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $SourceScript).Hash
$dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $RuntimeScript).Hash
if ($srcHash -ne $dstHash) { throw "Runtime copy hash mismatch." }
Write-Host ("Runtime SHA256 verified: " + $dstHash) -ForegroundColor Green

$argParts = @($py.Prefix) + @(
    ('"' + $RuntimeScript + '"'),
    "--root", ('"' + $Root + '"'),
    "--deploy", ('"' + $Deploy + '"'),
    "--remote", ('"' + $Remote + '"'),
    "--poll-seconds", "60"
)
$arguments = ($argParts -join " ")
$action = New-ScheduledTaskAction -Execute $py.Exe -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 20 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 5
$health = Join-Path $Root "orchestrator_health.json"
if (Test-Path -LiteralPath $health) {
    Write-Host "Orchestrator health:" -ForegroundColor Green
    Get-Content -LiteralPath $health -Raw | Write-Host
} else {
    Write-Host "Task installed and started. Health file has not appeared yet; Task Scheduler restart policy remains active." -ForegroundColor Yellow
}

Write-Host "=== INSTALL COMPLETE ===" -ForegroundColor Green
Write-Host "From now on the local worker polls GitHub main every 60 seconds and executes frozen queued jobs automatically."
