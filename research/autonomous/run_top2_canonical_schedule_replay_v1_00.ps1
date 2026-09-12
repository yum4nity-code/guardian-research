param(
    [string]$TerminalExe = "D:\MT5_FundedNext\terminal64.exe",
    [string]$PhaseIbRoot = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1",
    [string]$OutputDir = "D:\MT5_Backtests\Research\Autonomous\top2_mt5_canonical_replay_v1",
    [string]$ProgressFile = "D:\MT5_Backtests\Research\Autonomous\progress\TOP2-XAU-MT5-CANONICAL-REPLAY-R1.json"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

function Write-Progress([int]$completed,[int]$total,[string]$stage,[hashtable]$extra=@{}) {
    $o=[ordered]@{completed=$completed;total=$total;stage=$stage;updated_at_utc=[DateTime]::UtcNow.ToString("o")}
    foreach($k in $extra.Keys){$o[$k]=$extra[$k]}
    $d=Split-Path -Parent $ProgressFile; New-Item -ItemType Directory -Force -Path $d|Out-Null
    $tmp="$ProgressFile.tmp"; $o|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $tmp -Encoding UTF8; Move-Item $tmp $ProgressFile -Force
}

function Same-Terminal([string]$exe){
    $target=[IO.Path]::GetFullPath($exe).ToLowerInvariant(); $out=@()
    foreach($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)){
        try{if($p.Path -and [IO.Path]::GetFullPath($p.Path).ToLowerInvariant() -eq $target){$out+=$p}}catch{}
    }
    return @($out)
}

function Compile-Replay([string]$Source,[string]$Target,[string]$MetaEditor,[string]$Log){
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target)|Out-Null
    Copy-Item $Source $Target -Force
    $ex5=[IO.Path]::ChangeExtension($Target,'.ex5'); if(Test-Path $ex5){Remove-Item $ex5 -Force}; if(Test-Path $Log){Remove-Item $Log -Force}
    $p=Start-Process -FilePath $MetaEditor -ArgumentList @("/compile:$Target","/log:$Log") -Wait -PassThru
    if(-not (Test-Path $ex5)){throw "Replay EA compile failed for $Target exit=$($p.ExitCode)"}
}

function Run-Replay([string]$Candidate,[string]$ExpertRel,[string]$Ini,[string]$Report,[string]$CommonTrade,[int]$Step){
    if(Test-Path $Report){Remove-Item $Report -Force}; if(Test-Path $CommonTrade){Remove-Item $CommonTrade -Force}
    @"
[Common]
NewsEnable=1

[Experts]
AllowLiveTrading=0
AllowDllImport=0
Enabled=1

[Tester]
Expert=$ExpertRel
Symbol=XAUUSD
Period=M1
Model=1
ExecutionMode=0
Optimization=0
FromDate=2024.01.01
ToDate=2025.12.31
ForwardMode=0
Deposit=100000
Currency=USD
Leverage=100
Report=$Report
ReplaceReport=1
ShutdownTerminal=1
Visual=0
UseLocal=1
UseRemote=0
UseCloud=0
"@ | Set-Content -LiteralPath $Ini -Encoding ASCII
    Write-Progress $Step 5 'strategy_tester_canonical_replay' @{candidate_id=$Candidate}
    $proc=Start-Process -FilePath $TerminalExe -ArgumentList @('/portable',"/config:$Ini") -PassThru
    $deadline=(Get-Date).AddHours(3)
    while((Get-Date)-lt $deadline){Start-Sleep 5;try{if($proc.HasExited){break}}catch{break};Write-Progress $Step 5 'strategy_tester_canonical_replay' @{candidate_id=$Candidate;pid=$proc.Id}}
    $alive=$false;try{$alive=-not $proc.HasExited}catch{}
    if($alive){try{Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue}catch{};throw "$Candidate canonical replay exceeded 3 hours"}
    if(-not (Test-Path $CommonTrade)){throw "$Candidate replay ended without trade CSV"}
    $rows=@(Import-Csv $CommonTrade -Delimiter ';'); if($rows.Count -lt 20){throw "$Candidate replay produced too few trades: $($rows.Count)"}
    Copy-Item $CommonTrade (Join-Path $OutputDir ("$Candidate"+'_TRADES.csv')) -Force
}

$TerminalExe=[IO.Path]::GetFullPath($TerminalExe); if(-not(Test-Path $TerminalExe)){throw "Terminal missing: $TerminalExe"}
$InstallDir=Split-Path -Parent $TerminalExe; $MetaEditor=Join-Path $InstallDir 'metaeditor64.exe'; if(-not(Test-Path $MetaEditor)){throw 'MetaEditor missing'}
$existing=@(Same-Terminal $TerminalExe)
if($existing.Count -gt 0){
    $deadline=(Get-Date).AddMinutes(20)
    while((Get-Date)-lt $deadline -and @(Same-Terminal $TerminalExe).Count -gt 0){Write-Progress 0 5 'waiting_for_fundednext_terminal_to_close' @{action='Close visible FundedNext terminal; harness will not terminate it.'};Start-Sleep 3}
    if(@(Same-Terminal $TerminalExe).Count -gt 0){throw 'FundedNext terminal remained open; replay harness refused to stop or reuse it.'}
}

New-Item -ItemType Directory -Force -Path $OutputDir|Out-Null
$RepoRoot=$env:GUARDIAN_DEPLOY_ROOT; if(-not $RepoRoot){throw 'GUARDIAN_DEPLOY_ROOT is not set'}
$Common=Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files\Guardian\top2_replay'; New-Item -ItemType Directory -Force -Path $Common|Out-Null
Write-Progress 0 5 'prepare_canonical_schedules'
& python (Join-Path $RepoRoot 'research\autonomous\prepare_top2_canonical_schedule_replay_v1_00.py') --phase-ib-root $PhaseIbRoot --common-dir $Common --output-dir $OutputDir
if($LASTEXITCODE -ne 0){throw 'canonical schedule generation failed'}

$ExpertDir=Join-Path $InstallDir 'MQL5\Experts\GuardianResearch'; $src=Join-Path $RepoRoot 'research\ea\Top2_CanonicalScheduleReplayTester_v1_00.mq5'
$t347=Join-Path $ExpertDir 'R6B-347_CanonicalReplay_v1_00.mq5'; $t307=Join-Path $ExpertDir 'R6B-307_CanonicalReplay_v1_00.mq5'
Write-Progress 1 5 'compile_replay_eas'
Compile-Replay $src $t347 $MetaEditor (Join-Path $OutputDir 'R6B-347_replay_compile.log')
Compile-Replay $src $t307 $MetaEditor (Join-Path $OutputDir 'R6B-307_replay_compile.log')

$csv347=Join-Path $Common 'R6B-347_XAUUSD_TRADES.csv'; $csv307=Join-Path $Common 'R6B-307_XAUUSD_TRADES.csv'
Run-Replay 'R6B-347' 'GuardianResearch\R6B-347_CanonicalReplay_v1_00.ex5' (Join-Path $OutputDir 'R6B-347_replay.ini') (Join-Path $OutputDir 'R6B-347_replay_report.xml') $csv347 2
$deadline=(Get-Date).AddMinutes(2);while((Get-Date)-lt $deadline -and @(Same-Terminal $TerminalExe).Count -gt 0){Start-Sleep 2};if(@(Same-Terminal $TerminalExe).Count -gt 0){throw 'tester remained open after R6B-347'}
Run-Replay 'R6B-307' 'GuardianResearch\R6B-307_CanonicalReplay_v1_00.ex5' (Join-Path $OutputDir 'R6B-307_replay.ini') (Join-Path $OutputDir 'R6B-307_replay_report.xml') $csv307 3

$summary=[ordered]@{schema=1;phase='top2-xau-mt5-canonical-replay';status='PASS';generated_at_utc=[DateTime]::UtcNow.ToString('o');window='2024-01-01 through 2025-12-31 only';protected_2026_opened=$false;signal_recomputed_in_mt5=$false;method='exact canonical schedule replay'}
$summary|ConvertTo-Json -Depth 6|Set-Content (Join-Path $OutputDir 'top2_mt5_canonical_replay_summary.json') -Encoding UTF8
Write-Progress 5 5 'complete' @{status='PASS';protected_2026_opened=$false}
$summary|ConvertTo-Json -Compress
