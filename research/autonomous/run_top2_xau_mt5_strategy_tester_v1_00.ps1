param(
    [string]$TerminalExe = "D:\MT5_FundedNext\terminal64.exe",
    [string]$OutputDir = "D:\MT5_Backtests\Research\Autonomous\top2_mt5_strategy_tester_v1",
    [string]$ProgressFile = "D:\MT5_Backtests\Research\Autonomous\progress\TOP2-XAU-MT5-STRATEGY-TESTER-R1.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Progress([int]$completed,[int]$total,[string]$stage,[hashtable]$extra=@{}) {
    $o = [ordered]@{
        completed = $completed
        total = $total
        stage = $stage
        updated_at_utc = [DateTime]::UtcNow.ToString("o")
    }
    foreach($k in $extra.Keys){ $o[$k] = $extra[$k] }
    $dir = Split-Path -Parent $ProgressFile
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $tmp = "$ProgressFile.tmp"
    $o | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $ProgressFile -Force
}

function Get-SameTerminalProcess([string]$exe) {
    $target = [IO.Path]::GetFullPath($exe).TrimEnd('\').ToLowerInvariant()
    $out = @()
    foreach($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)) {
        try {
            if($p.Path -and ([IO.Path]::GetFullPath($p.Path).TrimEnd('\').ToLowerInvariant() -eq $target)) {
                $out += $p
            }
        } catch {}
    }
    return @($out)
}

function Compile-EA([string]$Source,[string]$Target,[string]$MetaEditor,[string]$LogPath) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target -Force
    $ex5 = [IO.Path]::ChangeExtension($Target, ".ex5")
    if(Test-Path -LiteralPath $ex5){ Remove-Item -LiteralPath $ex5 -Force }
    if(Test-Path -LiteralPath $LogPath){ Remove-Item -LiteralPath $LogPath -Force }
    $cp = Start-Process -FilePath $MetaEditor -ArgumentList @("/compile:$Target","/log:$LogPath") -Wait -PassThru
    if(-not (Test-Path -LiteralPath $ex5)) {
        $tail = ""
        if(Test-Path -LiteralPath $LogPath) {
            try { $tail = (Get-Content -LiteralPath $LogPath -Encoding Unicode -Tail 40) -join [Environment]::NewLine } catch {}
        }
        throw "Compilation failed for $Source. MetaEditor exit=$($cp.ExitCode). $tail"
    }
    return $ex5
}

function Run-Test([string]$Candidate,[string]$ExpertRel,[string]$IniPath,[string]$ReportPath,[string]$TradeCsv,[int]$Index) {
    if(Test-Path -LiteralPath $ReportPath){ Remove-Item -LiteralPath $ReportPath -Force }
    if(Test-Path -LiteralPath $TradeCsv){ Remove-Item -LiteralPath $TradeCsv -Force }

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
FromDate=2016.12.01
ToDate=2026.07.31
ForwardMode=0
Deposit=100000
Currency=USD
Leverage=100
Report=$ReportPath
ReplaceReport=1
ShutdownTerminal=1
Visual=0
UseLocal=1
UseRemote=0
UseCloud=0
"@ | Set-Content -LiteralPath $IniPath -Encoding ASCII

    Write-Progress $Index 4 "strategy_tester_running" @{candidate_id=$Candidate; report=$ReportPath}
    $proc = Start-Process -FilePath $TerminalExe -ArgumentList @("/portable","/config:$IniPath") -PassThru

    $deadline = (Get-Date).AddHours(4)
    while((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        try {
            if($proc.HasExited) { break }
        } catch { break }
        Write-Progress $Index 4 "strategy_tester_running" @{candidate_id=$Candidate; pid=$proc.Id}
    }

    $still = $false
    try { $still = -not $proc.HasExited } catch {}
    if($still) {
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        throw "$Candidate Strategy Tester exceeded 4 hours and was stopped."
    }

    if(-not (Test-Path -LiteralPath $TradeCsv)) {
        throw "$Candidate Strategy Tester ended without its trade CSV: $TradeCsv"
    }
    $rows = @(Import-Csv -LiteralPath $TradeCsv -Delimiter ';')
    if($rows.Count -lt 20) {
        throw "$Candidate Strategy Tester produced too few closed trades: $($rows.Count)"
    }

    $destCsv = Join-Path $OutputDir ("$Candidate" + "_TRADES.csv")
    Copy-Item -LiteralPath $TradeCsv -Destination $destCsv -Force

    $reportExists = Test-Path -LiteralPath $ReportPath
    return [pscustomobject]@{
        candidate_id = $Candidate
        trades = $rows.Count
        trade_csv = $destCsv
        report = $ReportPath
        report_exists = $reportExists
        exit_code = $(try { $proc.ExitCode } catch { $null })
    }
}

$TerminalExe = [IO.Path]::GetFullPath($TerminalExe)
if(-not (Test-Path -LiteralPath $TerminalExe)){ throw "Terminal missing: $TerminalExe" }
$InstallDir = Split-Path -Parent $TerminalExe
$MetaEditor = Join-Path $InstallDir "metaeditor64.exe"
if(-not (Test-Path -LiteralPath $MetaEditor)){ throw "MetaEditor missing: $MetaEditor" }

$existing = @(Get-SameTerminalProcess $TerminalExe)
if($existing.Count -gt 0) {
    throw "FundedNext terminal is already open (PID(s): $($existing.Id -join ',')). Close that window first; this harness refuses to stop or reuse a live terminal."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$RepoRoot = $env:GUARDIAN_DEPLOY_ROOT
if(-not $RepoRoot){ throw "GUARDIAN_DEPLOY_ROOT is not set" }

$ExpertDir = Join-Path $InstallDir "MQL5\Experts\GuardianResearch"
$src347 = Join-Path $RepoRoot "research\ea\R6B-347_LongHistoryTester_v1_00.mq5"
$src307 = Join-Path $RepoRoot "research\ea\R6B-307_LongHistoryTester_v1_00.mq5"
$tgt347 = Join-Path $ExpertDir "R6B-347_LongHistoryTester_v1_00.mq5"
$tgt307 = Join-Path $ExpertDir "R6B-307_LongHistoryTester_v1_00.mq5"

Write-Progress 0 4 "compile_r6b347"
$null = Compile-EA $src347 $tgt347 $MetaEditor (Join-Path $OutputDir "R6B-347_compile.log")
Write-Progress 1 4 "compile_r6b307"
$null = Compile-EA $src307 $tgt307 $MetaEditor (Join-Path $OutputDir "R6B-307_compile.log")

$Common = Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files\Guardian\top2"
New-Item -ItemType Directory -Force -Path $Common | Out-Null

$ini347 = Join-Path $OutputDir "R6B-347_tester.ini"
$ini307 = Join-Path $OutputDir "R6B-307_tester.ini"
$rep347 = Join-Path $OutputDir "R6B-347_report.xml"
$rep307 = Join-Path $OutputDir "R6B-307_report.xml"
$csv347 = Join-Path $Common "R6B-347_XAUUSD_TRADES.csv"
$csv307 = Join-Path $Common "R6B-307_XAUUSD_TRADES.csv"

$r347 = Run-Test "R6B-347" "GuardianResearch\R6B-347_LongHistoryTester_v1_00.ex5" $ini347 $rep347 $csv347 2

$deadline = (Get-Date).AddMinutes(2)
while((Get-Date) -lt $deadline -and @(Get-SameTerminalProcess $TerminalExe).Count -gt 0){ Start-Sleep 2 }
if(@(Get-SameTerminalProcess $TerminalExe).Count -gt 0){ throw "FundedNext tester process remained open after R6B-347; refusing to overlap tester runs." }

$r307 = Run-Test "R6B-307" "GuardianResearch\R6B-307_LongHistoryTester_v1_00.ex5" $ini307 $rep307 $csv307 3

$summary = [ordered]@{
    schema = 1
    phase = "top2-xau-mt5-strategy-tester"
    status = "PASS"
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    tester_model = "1 minute OHLC"
    tester_period = "M1"
    requested_active_window = "2017-01-01 through 2026-07-31"
    warmup_from = "2016-12-01"
    live_trading = $false
    results = @($r347,$r307)
}
$summaryPath = Join-Path $OutputDir "top2_mt5_strategy_tester_summary.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
Write-Progress 4 4 "complete" @{status="PASS"; summary=$summaryPath}
$summary | ConvertTo-Json -Compress -Depth 8
