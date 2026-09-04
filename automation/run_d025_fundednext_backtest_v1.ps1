param(
    [string]$FromDate = '2025.01.01',
    [string]$ToDate = '2026.06.28',
    [string]$HostSymbol = 'BTCUSD',
    [string]$Symbol1 = 'BTCUSD',
    [string]$Symbol2 = 'ETHUSD',
    [string]$TerminalDataPath = '',
    [int]$TimeoutMinutes = 480,
    [switch]$NoGitHubPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$SourceEa = Join-Path $RepoRoot 'research\ea\D025_LER_Observer_V0.mq5'
$RulesLock = Join-Path $RepoRoot 'research\campaigns\D025_LER_V0_RULES_LOCK_2026_09_04.md'
$Analyzer = Join-Path $RepoRoot 'automation\analyze_d025_backtest_v1.py'
$CommonFiles = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$RunStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunId = "D025_FN_CORE_${RunStamp}"
$LocalRoot = "D:\MT5_Backtests\Research\D025\Backtests\$RunId"
$RawLocal = Join-Path $LocalRoot 'raw'
$PublishLocal = Join-Path $LocalRoot 'publish'
$WorkLocal = Join-Path $LocalRoot 'work'
$ResultsClone = 'D:\MT5_Backtests\guardian-backtest-results'
$ResultsBranch = 'backtest-results'

New-Item -ItemType Directory -Force -Path $RawLocal,$PublishLocal,$WorkLocal | Out-Null

function Write-Step([string]$Text) {
    Write-Host ''
    Write-Host ("=== {0} ===" -f $Text) -ForegroundColor Cyan
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Read-TailText([string]$Path, [int]$Lines = 2500) {
    try { return ((Get-Content -Path $Path -Tail $Lines -ErrorAction Stop) -join "`n") }
    catch { return '' }
}

function Clean-Origin([string]$Text) {
    if ($null -eq $Text) { return '' }
    return (($Text -replace "`0", '').Trim())
}

function Find-FundedNextTerminalData {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path $Explicit)) { throw "TerminalDataPath does not exist: $Explicit" }
        return (Resolve-Path $Explicit).Path
    }

    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    if (-not (Test-Path $terminalRoot)) { throw "MT5 terminal data root not found: $terminalRoot" }
    $candidates = @()
    foreach ($dir in Get-ChildItem $terminalRoot -Directory) {
        if ($dir.Name -eq 'Common') { continue }
        $mql5 = Join-Path $dir.FullName 'MQL5'
        if (-not (Test-Path $mql5)) { continue }
        $score = 0
        $evidence = @()
        $originPath = Join-Path $dir.FullName 'origin.txt'
        $origin = ''
        if (Test-Path $originPath) {
            try { $origin = Clean-Origin (Get-Content $originPath -Raw -ErrorAction Stop) } catch {}
            if ($origin -match '(?i)funded\s*next|fundednext') { $score += 200; $evidence += 'origin' }
        }

        $terminalLogs = Join-Path $dir.FullName 'logs'
        if (Test-Path $terminalLogs) {
            foreach ($lf in @(Get-ChildItem $terminalLogs -File -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 12)) {
                $text = Read-TailText $lf.FullName 4000
                if ($text -match '(?i)funded\s*next|fundednext') {
                    $score += 100
                    $evidence += "terminal:$($lf.Name)"
                    break
                }
            }
        }

        $mqlLogs = Join-Path $dir.FullName 'MQL5\Logs'
        if (Test-Path $mqlLogs) {
            foreach ($lf in @(Get-ChildItem $mqlLogs -File -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 8)) {
                $text = Read-TailText $lf.FullName 2500
                if ($text -match '(?i)funded\s*next|fundednext') {
                    $score += 10
                    $evidence += "mql:$($lf.Name)"
                    break
                }
            }
        }

        if ($score -gt 0) {
            $candidates += [pscustomobject]@{ DataPath=$dir.FullName; Score=$score; Origin=$origin; Evidence=($evidence -join ',') }
        }
    }
    if ($candidates.Count -eq 0) {
        throw 'No MT5 data folder containing FundedNext evidence was found. Re-run with -TerminalDataPath "C:\Users\...\AppData\Roaming\MetaQuotes\Terminal\<HASH>" if needed.'
    }
    $picked = $candidates | Sort-Object Score -Descending | Select-Object -First 1
    Write-Host ("FundedNext terminal selected: {0}" -f $picked.DataPath)
    Write-Host ("Detection score/evidence: {0} / {1}" -f $picked.Score,$picked.Evidence)
    return $picked.DataPath
}

function Resolve-TerminalInstall([string]$DataPath) {
    $originPath = Join-Path $DataPath 'origin.txt'
    if (-not (Test-Path $originPath)) { throw "origin.txt missing in $DataPath" }
    $origin = Clean-Origin (Get-Content $originPath -Raw)
    if (Test-Path $origin -PathType Leaf) { $origin = Split-Path $origin -Parent }
    $terminal = Join-Path $origin 'terminal64.exe'
    $editor = Join-Path $origin 'metaeditor64.exe'
    if (-not (Test-Path $terminal)) { throw "terminal64.exe not found from origin: $origin" }
    if (-not (Test-Path $editor)) { throw "metaeditor64.exe not found from origin: $origin" }
    return [pscustomobject]@{ Install=$origin; Terminal=$terminal; MetaEditor=$editor }
}

function Escape-MqlLiteral([string]$Value) {
    return $Value.Replace('\','\\').Replace('"','\"')
}

function Build-BacktestEa {
    param([string]$Source,[string]$Destination,[string]$Run,[string]$Sym1,[string]$Sym2)
    $src = Get-Content $Source -Raw
    $runEsc = Escape-MqlLiteral $Run
    $sym1Esc = Escape-MqlLiteral $Sym1
    $sym2Esc = Escape-MqlLiteral $Sym2
    $basePath = "GuardianResearch\\D025\\Backtests\\$runEsc"

    $src = [regex]::Replace($src, '#property description\s+"[^"]*"', '#property description "D025 LER V0 backtest harness - VIRTUAL ONLY"', 1)
    $src = [regex]::Replace($src, 'input string InpSymbol1\s*=\s*"[^"]*";', "input string InpSymbol1 = `"$sym1Esc`";", 1)
    $src = [regex]::Replace($src, 'input string InpSymbol2\s*=\s*"[^"]*";', "input string InpSymbol2 = `"$sym2Esc`";", 1)

    $ensure = @"
void EnsureCommonFolder()
{
   FolderCreate("GuardianResearch", FILE_COMMON);
   FolderCreate("GuardianResearch\\D025", FILE_COMMON);
   FolderCreate("GuardianResearch\\D025\\Backtests", FILE_COMMON);
   FolderCreate("$basePath", FILE_COMMON);
}
"@
    $src = [regex]::Replace($src, 'void EnsureCommonFolder\(\)\s*\{.*?\}', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $ensure }, [System.Text.RegularExpressions.RegexOptions]::Singleline)

    foreach ($pair in @(
        @{ Name='EventsFile'; File='events.csv' },
        @{ Name='TradesFile'; File='virtual_trades.csv' },
        @{ Name='OutcomesFile'; File='outcomes.csv' }
    )) {
        $rep = "string $($pair.Name)()`r`n{`r`n   return `"$basePath\\$($pair.File)`";`r`n}"
        $pattern = "string $($pair.Name)\(\)\s*\{.*?\}"
        $src = [regex]::Replace($src, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $rep }, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    }

    # Avoid a synthetic startup event from the last bar before FromDate.
    $src = $src.Replace('g_symbols[s].last_m15_closed_open = 0;', 'g_symbols[s].last_m15_closed_open = iTime(g_symbols[s].symbol, PERIOD_M15, 1);')
    $src = $src.Replace('g_symbols[s].last_m1_closed_open = 0;', 'g_symbols[s].last_m1_closed_open = iTime(g_symbols[s].symbol, PERIOD_M1, 1);')
    $src = $src.Replace('g_session_id = StringFormat("D025V0_%I64d_%I64d", (long)TimeGMT(), (long)GetTickCount64());', "g_session_id = StringFormat(`"BT_${runEsc}_%I64d`", (long)GetTickCount64());")

    # Backtests are tick-driven for speed. State rules still consume only CLOSED M15 bars and CLOSED M1 outcome bars.
    $src = [regex]::Replace($src, 'EventSetTimer\(MathMax\(1,InpTimerSeconds\)\);', '// Backtest harness: timer disabled; OnTick drives multi-symbol closed-bar processing.', 1)
    $onTick = @"
void OnTick()
{
   for(int s=0;s<SYMBOL_COUNT;s++)
   {
      if(!g_symbols[s].ready) continue;
      ProcessM15Symbol(s);
      ProcessM1Symbol(s);
   }
}
"@
    $src = [regex]::Replace($src, 'void OnTick\(\)\s*\{.*?\}', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $onTick }, [System.Text.RegularExpressions.RegexOptions]::Singleline)

    $sentinel = @"
   if(MQLInfoInteger(MQL_TESTER))
   {
      EnsureCommonFolder();
      int done_h = FileOpen("$basePath\\COMPLETE.txt", FILE_WRITE|FILE_TXT|FILE_COMMON|FILE_ANSI);
      if(done_h != INVALID_HANDLE)
      {
         FileWrite(done_h, "run_id=$runEsc");
         FileWrite(done_h, "completed_utc=" + TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS));
         FileWrite(done_h, "deinit_reason=" + IntegerToString(reason));
         FileWrite(done_h, "active_virtual_trades_at_end=" + IntegerToString(active_count));
         FileClose(done_h);
      }
   }
"@
    $src = $src.Replace('   Print("[D025][STOP] session=",g_session_id," reason=",reason," active_virtual_trades_lost_on_restart=",active_count);', $sentinel + "`r`n   Print(`"[D025][STOP] session=`",g_session_id,`" reason=`",reason,`" active_virtual_trades_lost_on_restart=`",active_count);")

    Set-Content -Path $Destination -Value $src -Encoding UTF8
}

function Find-Python {
    $venv = Join-Path $RepoRoot 'research\external_intelligence\.venv\Scripts\python.exe'
    if (Test-Path $venv) { return $venv }
    $p = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($p) { return $p.Source }
    throw 'Python not found. The Shared Intelligence venv or python.exe is required for the result analyzer.'
}

function Ensure-ResultsClone {
    $remote = (& git -C $RepoRoot remote get-url origin).Trim()
    if (-not (Test-Path (Join-Path $ResultsClone '.git'))) {
        if (Test-Path $ResultsClone) { Remove-Item -Recurse -Force $ResultsClone }
        & git clone --quiet $remote $ResultsClone
        if ($LASTEXITCODE -ne 0) { throw 'Could not clone results workspace.' }
    }
    & git -C $ResultsClone fetch --quiet origin $ResultsBranch
    if ($LASTEXITCODE -ne 0) { throw "Could not fetch origin/$ResultsBranch" }
    & git -C $ResultsClone checkout -q -B $ResultsBranch "origin/$ResultsBranch"
    if ($LASTEXITCODE -ne 0) { throw "Could not checkout $ResultsBranch" }
}

if (-not (Test-Path $SourceEa)) { throw "Missing D025 source: $SourceEa" }
if (-not (Test-Path $RulesLock)) { throw "Missing D025 rules lock: $RulesLock" }
if (-not (Test-Path $Analyzer)) { throw "Missing analyzer: $Analyzer" }
if (-not (Test-Path $CommonFiles)) { throw "MT5 Common Files not found: $CommonFiles" }

Write-Step '1/7 Locate FundedNext MT5 session'
$dataPath = Find-FundedNextTerminalData $TerminalDataPath
$install = Resolve-TerminalInstall $dataPath
Write-Host ("Terminal executable: {0}" -f $install.Terminal)
Write-Host ("Terminal build: {0}" -f (Get-Item $install.Terminal).VersionInfo.FileVersion)

Write-Step '2/7 Generate isolated D025 backtest harness'
$expertDir = Join-Path $dataPath 'MQL5\Experts\GuardianResearch\Backtests'
New-Item -ItemType Directory -Force -Path $expertDir | Out-Null
$eaBase = "D025_LER_BT_$RunId"
$generatedMq5 = Join-Path $expertDir ($eaBase + '.mq5')
$generatedEx5 = Join-Path $expertDir ($eaBase + '.ex5')
Build-BacktestEa -Source $SourceEa -Destination $generatedMq5 -Run $RunId -Sym1 $Symbol1 -Sym2 $Symbol2
Write-Host ("Generated: {0}" -f $generatedMq5)

Write-Step '3/7 Compile with FundedNext MetaEditor'
$compileLog = Join-Path $WorkLocal 'compile.log'
$compileArgs = "/compile:`"$generatedMq5`" /log:`"$compileLog`""
Start-Process -FilePath $install.MetaEditor -ArgumentList $compileArgs | Out-Null
$compileDeadline = (Get-Date).AddSeconds(90)
while (-not (Test-Path $generatedEx5)) {
    if ((Get-Date) -gt $compileDeadline) {
        $logText = if (Test-Path $compileLog) { Get-Content $compileLog -Raw } else { '(no compile log)' }
        throw "Compilation did not produce EX5 within 90 seconds.`n$logText"
    }
    Start-Sleep -Milliseconds 500
}
Start-Sleep -Seconds 1
if (Test-Path $compileLog) {
    $compileText = Get-Content $compileLog -Raw
    Write-Host ($compileText.Trim())
    if ($compileText -match '(?i)([1-9][0-9]*)\s+error') { throw 'D025 backtest harness compilation has errors.' }
}

Write-Step '4/7 Launch Strategy Tester on FundedNext session'
$commonRunDir = Join-Path $CommonFiles "GuardianResearch\D025\Backtests\$RunId"
if (Test-Path $commonRunDir) { Remove-Item -Recurse -Force $commonRunDir }
New-Item -ItemType Directory -Force -Path $commonRunDir | Out-Null
$sentinel = Join-Path $commonRunDir 'COMPLETE.txt'
$ini = Join-Path $WorkLocal 'tester.ini'
$expertRelative = "GuardianResearch\Backtests\$eaBase"
$iniText = @"
[Experts]
AllowLiveTrading=0
AllowDllImport=0

[Tester]
Expert=$expertRelative
Symbol=$HostSymbol
Period=M1
Model=4
ExecutionMode=0
Optimization=0
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Deposit=10000
Currency=USD
Leverage=1:100
ReplaceReport=1
ShutdownTerminal=0
"@
Set-Content -Path $ini -Value $iniText -Encoding ASCII
Write-Host "Run ID: $RunId"
Write-Host "Period: $FromDate -> $ToDate"
Write-Host "Symbols: $Symbol1 + $Symbol2 (host: $HostSymbol)"
Write-Host 'Model: 4 = Every tick based on real ticks'
Write-Host 'Safety: AllowLiveTrading=0; ShutdownTerminal=0'
Start-Process -FilePath $install.Terminal -ArgumentList "/config:`"$ini`"" | Out-Null

Write-Step '5/7 Wait for tester completion'
$startedAt = Get-Date
$deadline = $startedAt.AddMinutes($TimeoutMinutes)
$lastMessage = Get-Date
while (-not (Test-Path $sentinel)) {
    if ((Get-Date) -gt $deadline) { throw "Backtest timeout after $TimeoutMinutes minutes. Run preserved locally: $RunId" }
    if (((Get-Date) - $lastMessage).TotalSeconds -ge 30) {
        $elapsed = [math]::Round(((Get-Date) - $startedAt).TotalMinutes,1)
        Write-Host ("Backtest running... elapsed {0} min" -f $elapsed)
        $lastMessage = Get-Date
    }
    Start-Sleep -Seconds 3
}
Write-Host (Get-Content $sentinel -Raw)

foreach ($name in @('events.csv','virtual_trades.csv','outcomes.csv','COMPLETE.txt')) {
    $src = Join-Path $commonRunDir $name
    if (Test-Path $src) { Copy-Item $src (Join-Path $RawLocal $name) -Force }
}
if (-not (Test-Path (Join-Path $RawLocal 'events.csv'))) {
    throw 'Backtest completed but events.csv is missing. Check symbol names / tester journal before trusting this run.'
}

Write-Step '6/7 Analyze D025 results'
$python = Find-Python
$anArgs = @(
    $Analyzer,
    '--run-dir', $RawLocal,
    '--output-dir', $PublishLocal,
    '--run-id', $RunId,
    '--from-date', $FromDate,
    '--to-date', $ToDate,
    '--host-symbol', $HostSymbol,
    '--symbol1', $Symbol1,
    '--symbol2', $Symbol2,
    '--terminal-label', 'FundedNext',
    '--model', '4'
)
& $python @anArgs
if ($LASTEXITCODE -ne 0) { throw 'D025 analyzer failed.' }

$repoCommit = (& git -C $RepoRoot rev-parse HEAD).Trim()
$manifest = [ordered]@{
    schema = 1
    run_id = $RunId
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    source_branch = 'main'
    source_commit = $repoCommit
    d025_source = 'research/ea/D025_LER_Observer_V0.mq5'
    d025_source_sha256 = Get-Sha256 $SourceEa
    locked_rules = 'research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md'
    locked_rules_sha256 = Get-Sha256 $RulesLock
    generated_harness_sha256 = Get-Sha256 $generatedMq5
    tester_config_sha256 = Get-Sha256 $ini
    terminal = [ordered]@{
        label = 'FundedNext'
        build = (Get-Item $install.Terminal).VersionInfo.FileVersion
    }
    tester = [ordered]@{
        from_date = $FromDate
        to_date = $ToDate
        host_symbol = $HostSymbol
        symbol1 = $Symbol1
        symbol2 = $Symbol2
        period = 'M1'
        model = 4
        model_label = 'Every tick based on real ticks'
        optimization = $false
        live_trading_allowed = $false
        shutdown_terminal = $false
    }
    raw = [ordered]@{}
}
foreach ($name in @('events.csv','virtual_trades.csv','outcomes.csv','COMPLETE.txt')) {
    $p = Join-Path $RawLocal $name
    if (Test-Path $p) {
        $manifest.raw[$name] = [ordered]@{ size_bytes=(Get-Item $p).Length; sha256=Get-Sha256 $p }
    }
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $PublishLocal 'manifest.json') -Encoding UTF8

Write-Step '7/7 Publish compact results to GitHub'
if ($NoGitHubPush) {
    Write-Host 'GitHub push skipped by -NoGitHubPush.'
} else {
    Ensure-ResultsClone
    $dest = Join-Path $ResultsClone "backtests\d025\$RunId"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    foreach ($name in @('SUMMARY.md','summary.json','manifest.json')) {
        Copy-Item (Join-Path $PublishLocal $name) (Join-Path $dest $name) -Force
    }
    $compact = Join-Path $PublishLocal 'events_compact.csv'
    if ((Test-Path $compact) -and (Get-Item $compact).Length -le 5MB) {
        Copy-Item $compact (Join-Path $dest 'events_compact.csv') -Force
    }
    & git -C $ResultsClone add -- "backtests/d025/$RunId"
    & git -C $ResultsClone -c user.name='Guardian Backtest Bot' -c user.email='guardian-backtest@local' commit -m "D025 FundedNext backtest $RunId"
    if ($LASTEXITCODE -ne 0) { throw 'git commit of backtest result failed.' }
    & git -C $ResultsClone push origin $ResultsBranch
    if ($LASTEXITCODE -ne 0) { throw 'git push of backtest result failed.' }
    Write-Host "Published: branch $ResultsBranch / backtests/d025/$RunId"
}

Write-Host ''
Write-Host 'D025 FUNDEDNEXT BACKTEST: COMPLETE' -ForegroundColor Green
Write-Host ("Local raw results : {0}" -f $RawLocal)
Write-Host ("Local summary     : {0}" -f (Join-Path $PublishLocal 'SUMMARY.md'))
Write-Host ("GitHub branch     : {0}" -f $ResultsBranch)
Write-Host ("Run ID            : {0}" -f $RunId)
