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
$PhaseIcEngine = Join-Path $PSScriptRoot "..\research\autonomous\phase_ic_xau_phenomenon_atlas_v1_00.py"
$PhaseIcTest = Join-Path $PSScriptRoot "..\research\autonomous\test_phase_ic_xau_phenomenon_atlas_v1_00.py"

function Find-Python {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return [pscustomobject]@{ Exe=$py.Source; Prefix=@("-3") } }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return [pscustomobject]@{ Exe=$python.Source; Prefix=@() } }
    throw "Python 3 not found."
}

Write-Host "=== GUARDIAN AUTONOMOUS RESEARCH ORCHESTRATOR installer v1.02 ===" -ForegroundColor Cyan
foreach ($p in @($SourceScript,$TestScript,$PhaseIcEngine,$PhaseIcTest)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing installer dependency: $p" }
}
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { throw "git.exe not found in PATH." }

$py = Find-Python
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

Write-Host "Running isolated orchestrator tests..."
& $py.Exe @($py.Prefix) $TestScript | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Orchestrator tests failed; refusing installation." }

Write-Host "Running frozen Phase I-C invariant tests..."
& $py.Exe @($py.Prefix) $PhaseIcTest | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Phase I-C invariant tests failed; refusing installation." }

Write-Host "Compiling autonomous Python entrypoints..."
& $py.Exe @($py.Prefix) -m py_compile $SourceScript $PhaseIcEngine
if ($LASTEXITCODE -ne 0) { throw "Autonomous Python compile failed." }

Copy-Item -LiteralPath $SourceScript -Destination $RuntimeScript -Force
$srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $SourceScript).Hash
$dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $RuntimeScript).Hash
if ($srcHash -ne $dstHash) { throw "Runtime copy hash mismatch." }
Write-Host ("Runtime SHA256 verified: " + $dstHash) -ForegroundColor Green

# End-to-end dry reconciliation before persistence. WAITING is a valid success while I-B is not PASS.
Write-Host "Running one end-to-end dry reconciliation..."
& $py.Exe @($py.Prefix) $RuntimeScript --root $Root --deploy $Deploy --remote $Remote --once --no-publish | Out-Host
if ($LASTEXITCODE -ne 0) { throw "End-to-end orchestrator dry run failed; refusing Scheduled Task installation." }
$health = Join-Path $Root "orchestrator_health.json"
if (-not (Test-Path -LiteralPath $health)) { throw "Dry run returned success but wrote no health file." }
Write-Host "Dry-run health:" -ForegroundColor Green
Get-Content -LiteralPath $health -Raw | Write-Host

$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$argParts = @($py.Prefix) + @(
    ('"' + $RuntimeScript + '"'),
    "--root", ('"' + $Root + '"'),
    "--deploy", ('"' + $Deploy + '"'),
    "--remote", ('"' + $Remote + '"'),
    "--poll-seconds", "60"
)
$arguments = ($argParts -join " ")
$action = New-ScheduledTaskAction -Execute $py.Exe -Argument $arguments -WorkingDirectory $RuntimeDir
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 20 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Guardian deterministic autonomous research executor. Polls frozen GitHub research queue; 2026 fail-closed."

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$installed = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Task installed and started." -ForegroundColor Green
Write-Host ("State: " + $installed.State)
Write-Host ("Last result: " + $info.LastTaskResult)
Write-Host "=== INSTALL COMPLETE ===" -ForegroundColor Green
Write-Host "The local worker now polls GitHub main every 60 seconds and executes only frozen queued jobs."
