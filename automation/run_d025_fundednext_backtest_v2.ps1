param(
    [string]$FromDate = '2025.01.01',
    [string]$ToDate = '2026.06.28',
    [string]$HostSymbol = 'BTCUSD',
    [string]$Symbol1 = 'BTCUSD',
    [string]$Symbol2 = 'ETHUSD',
    [string]$TargetAccount = '14202634',
    [string]$TargetServer = 'FundedNext-Server 2',
    [string]$TerminalDataPath = '',
    [int]$TimeoutMinutes = 480,
    [switch]$NoGitHubPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$SourceEa = Join-Path $RepoRoot 'research\ea\D025_LER_Observer_V0.mq5'
$RulesLock = Join-Path $RepoRoot 'research\campaigns\D025_LER_V0_RULES_LOCK_2026_09_04.md'
$Publisher = Join-Path $RepoRoot 'automation\publish_d025_backtest_results_v1.ps1'
$GlobalCommonFiles = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$RunStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunId = "D025_FN2_CORE_${RunStamp}"
$LocalRoot = "D:\MT5_Backtests\Research\D025\Backtests\$RunId"
$RawLocal = Join-Path $LocalRoot 'raw'
$PublishLocal = Join-Path $LocalRoot 'publish'
$WorkLocal = Join-Path $LocalRoot 'work'
$PortableRoot = "D:\MT5_Backtests\Terminals\FundedNext_14202634_D025_BT"
$TargetStateFile = 'D:\MT5_Backtests\Research\D025\fundednext_target_14202634.json'

New-Item -ItemType Directory -Force -Path $RawLocal,$PublishLocal,$WorkLocal,(Split-Path $TargetStateFile -Parent) | Out-Null

function Step([string]$Text) {
    Write-Host ''
    Write-Host ("=== {0} ===" -f $Text) -ForegroundColor Cyan
}

function Clean([string]$Text) {
    if ($null -eq $Text) { return '' }
    return (($Text -replace "`0", '').Trim())
}

function Tail([string]$Path,[int]$Lines=3000) {
    try { return ((Get-Content -Path $Path -Tail $Lines -ErrorAction Stop) -join "`n") }
    catch { return '' }
}

function Has-ServerEvidence([string]$DataPath) {
    $serverRegex = [regex]::Escape($TargetServer)
    $bases = Join-Path $DataPath 'bases'
    if (Test-Path $bases) {
        foreach ($d in @(Get-ChildItem $bases -Directory -ErrorAction SilentlyContinue)) {
            if ($d.Name -match $serverRegex) { return $true }
        }
    }
    $logs = Join-Path $DataPath 'logs'
    if (Test-Path $logs) {
        foreach ($f in @(Get-ChildItem $logs -File -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 25)) {
            if ((Tail $f.FullName 5000) -match $serverRegex) { return $true }
        }
    }
    return $false
}

function Score-Target([string]$DataPath) {
    $serverRegex = [regex]::Escape($TargetServer)
    $accountRegex = [regex]::Escape($TargetAccount)
    $score = 0
    $evidence = @()

    $bases = Join-Path $DataPath 'bases'
    if (Test-Path $bases) {
        foreach ($d in @(Get-ChildItem $bases -Directory -ErrorAction SilentlyContinue)) {
            if ($d.Name -match $serverRegex) { $score += 600; $evidence += "bases:$($d.Name)"; break }
        }
    }

    foreach ($ld in @((Join-Path $DataPath 'logs'),(Join-Path $DataPath 'MQL5\Logs'))) {
        if (-not (Test-Path $ld)) { continue }
        foreach ($f in @(Get-ChildItem $ld -File -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 30)) {
            $t = Tail $f.FullName 6000
            if ($t -match $serverRegex) { $score += 300; $evidence += "server:$($f.Name)" }
            if ($t -match $accountRegex) { $score += 300; $evidence += "account:$($f.Name)" }
            if (($t -match $serverRegex) -and ($t -match $accountRegex)) { $score += 500 }
            if ($score -ge 1400) { break }
        }
    }

    return [pscustomobject]@{DataPath=$DataPath;Score=$score;Evidence=($evidence | Select-Object -Unique) -join ','}
}

function Find-ExactTarget {
    if ($TerminalDataPath) {
        if (-not (Test-Path $TerminalDataPath)) { throw "TerminalDataPath missing: $TerminalDataPath" }
        if (-not (Has-ServerEvidence $TerminalDataPath)) { throw "Explicit TerminalDataPath has no evidence for $TargetServer" }
        return (Resolve-Path $TerminalDataPath).Path
    }

    if (Test-Path $TargetStateFile) {
        try {
            $saved = Get-Content $TargetStateFile -Raw | ConvertFrom-Json
            if ($saved.data_path -and (Test-Path $saved.data_path) -and (Has-ServerEvidence $saved.data_path)) {
                Write-Host "Reusing memorized exact target: $($saved.data_path)"
                return (Resolve-Path $saved.data_path).Path
            }
        } catch {}
    }

    $root = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    $candidates = @()
    foreach ($d in @(Get-ChildItem $root -Directory -ErrorAction SilentlyContinue)) {
        if ($d.Name -eq 'Common') { continue }
        if (-not (Test-Path (Join-Path $d.FullName 'MQL5'))) { continue }
        $s = Score-Target $d.FullName
        if ($s.Score -gt 0) { $candidates += $s }
    }
    if ($candidates.Count -eq 0) { throw "No MT5 data folder matched $TargetServer / account $TargetAccount." }
    $ordered = @($candidates | Sort-Object Score -Descending)
    $picked = $ordered[0]
    if ($picked.Score -lt 600) { throw "Target confidence too low. Best candidate score=$($picked.Score), evidence=$($picked.Evidence)" }
    if ($ordered.Count -gt 1 -and $ordered[1].Score -eq $picked.Score) {
        throw "Ambiguous exact FundedNext target. Top candidates tie at score $($picked.Score)."
    }
    [ordered]@{account=$TargetAccount;server=$TargetServer;data_path=$picked.DataPath;evidence=$picked.Evidence;saved_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content $TargetStateFile -Encoding UTF8
    Write-Host "Exact target selected: $($picked.DataPath)"
    Write-Host "Evidence: $($picked.Evidence)"
    return $picked.DataPath
}

function Resolve-Install([string]$DataPath) {
    $originFile = Join-Path $DataPath 'origin.txt'
    if (-not (Test-Path $originFile)) { throw "origin.txt missing in target data folder." }
    $origin = Clean (Get-Content $originFile -Raw)
    if (Test-Path $origin -PathType Leaf) { $origin = Split-Path $origin -Parent }
    $terminal = Join-Path $origin 'terminal64.exe'
    $editor = Join-Path $origin 'metaeditor64.exe'
    if (-not (Test-Path $terminal)) { throw "terminal64.exe missing: $terminal" }
    if (-not (Test-Path $editor)) { throw "metaeditor64.exe missing: $editor" }
    return [pscustomobject]@{Root=$origin;Terminal=$terminal;MetaEditor=$editor}
}

function Robo([string]$Source,[string]$Dest,[string[]]$Extra=@()) {
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $args = @($Source,$Dest,'/E','/R:1','/W:1','/NFL','/NDL','/NJH','/NJS','/NP') + $Extra
    & robocopy @args | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "robocopy failed ($LASTEXITCODE): $Source -> $Dest" }
}

function Prepare-Portable([string]$DataPath,$Install) {
    Step '2/8 Prepare isolated portable FundedNext Server2 clone'
    Robo $Install.Root $PortableRoot @('/XD','MQL5','bases','config','logs','tester','profiles')
    $sourceConfig = Join-Path $DataPath 'config'
    if (-not (Test-Path $sourceConfig)) { throw 'Target MT5 config folder missing; cannot clone saved account context.' }
    Robo $sourceConfig (Join-Path $PortableRoot 'config') @('/MIR')

    $sourceBases = Join-Path $DataPath 'bases'
    if (Test-Path $sourceBases) {
        $serverDir = @(Get-ChildItem $sourceBases -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*$TargetServer*" } | Select-Object -First 1)
        if ($serverDir.Count -gt 0) {
            $destServer = Join-Path (Join-Path $PortableRoot 'bases') $serverDir[0].Name
            Robo $serverDir[0].FullName $destServer @('/XD',(Join-Path $serverDir[0].FullName 'history'),(Join-Path $serverDir[0].FullName 'ticks'))
        }
    }

    New-Item -ItemType Directory -Force -Path (Join-Path $PortableRoot 'MQL5\Experts\GuardianResearch\Backtests') | Out-Null
    Set-Content -Path (Join-Path $PortableRoot 'origin.txt') -Value $PortableRoot -Encoding ASCII
    Write-Host "Portable clone: $PortableRoot"
    Write-Host 'Live FundedNext terminal is NOT closed or modified.'
}

function Escape-Mql([string]$Value) { return $Value.Replace('\','\\').Replace('"','\"') }

function Build-Harness([string]$Destination) {
    $src = Get-Content $SourceEa -Raw
    $runEsc = Escape-Mql $RunId
    $s1 = Escape-Mql $Symbol1
    $s2 = Escape-Mql $Symbol2
    $basePath = "GuardianResearch\\D025\\Backtests\\$runEsc"

    $src = [regex]::Replace($src,'#property description\s+"[^"]*"','#property description "D025 LER V0 portable backtest harness - VIRTUAL ONLY"',1)
    $src = [regex]::Replace($src,'input string InpSymbol1\s*=\s*"[^"]*";',"input string InpSymbol1 = `"$s1`";",1)
    $src = [regex]::Replace($src,'input string InpSymbol2\s*=\s*"[^"]*";',"input string InpSymbol2 = `"$s2`";",1)

    $ensure = @"
void EnsureCommonFolder()
{
   FolderCreate("GuardianResearch", FILE_COMMON);
   FolderCreate("GuardianResearch\\D025", FILE_COMMON);
   FolderCreate("GuardianResearch\\D025\\Backtests", FILE_COMMON);
   FolderCreate("$basePath", FILE_COMMON);
}
"@
    $src = [regex]::Replace($src,'void EnsureCommonFolder\(\)\s*\{.*?\}',[System.Text.RegularExpressions.MatchEvaluator]{param($m)$ensure},[System.Text.RegularExpressions.RegexOptions]::Singleline)
    foreach ($p in @(@{N='EventsFile';F='events.csv'},@{N='TradesFile';F='virtual_trades.csv'},@{N='OutcomesFile';F='outcomes.csv'})) {
        $rep = "string $($p.N)()`r`n{`r`n   return `"$basePath\\$($p.F)`";`r`n}"
        $src = [regex]::Replace($src,"string $($p.N)\(\)\s*\{.*?\}",[System.Text.RegularExpressions.MatchEvaluator]{param($m)$rep},[System.Text.RegularExpressions.RegexOptions]::Singleline)
    }
    $src = $src.Replace('g_symbols[s].last_m15_closed_open = 0;','g_symbols[s].last_m15_closed_open = iTime(g_symbols[s].symbol, PERIOD_M15, 1);')
    $src = $src.Replace('g_symbols[s].last_m1_closed_open = 0;','g_symbols[s].last_m1_closed_open = iTime(g_symbols[s].symbol, PERIOD_M1, 1);')
    $src = $src.Replace('g_session_id = StringFormat("D025V0_%I64d_%I64d", (long)TimeGMT(), (long)GetTickCount64());',"g_session_id = StringFormat(`"BT_${runEsc}_%I64d`", (long)GetTickCount64());")
    $src = [regex]::Replace($src,'EventSetTimer\(MathMax\(1,InpTimerSeconds\)\);','// tester: timer disabled; OnTick drives closed-bar processing.',1)
    $tick = @"
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
    $src = [regex]::Replace($src,'void OnTick\(\)\s*\{.*?\}',[System.Text.RegularExpressions.MatchEvaluator]{param($m)$tick},[System.Text.RegularExpressions.RegexOptions]::Singleline)
    $done = @"
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
    $needle = '   Print("[D025][STOP] session=",g_session_id," reason=",reason," active_virtual_trades_lost_on_restart=",active_count);'
    $src = $src.Replace($needle,$done+"`r`n"+$needle)
    Set-Content -Path $Destination -Value $src -Encoding UTF8
}

function Find-OutputDir {
    $rel = "GuardianResearch\D025\Backtests\$RunId"
    $cands = @(
        (Join-Path $GlobalCommonFiles $rel),
        (Join-Path (Join-Path $PortableRoot 'Common\Files') $rel)
    )
    foreach ($c in $cands) { if (Test-Path (Join-Path $c 'COMPLETE.txt')) { return $c } }
    return $null
}

if (-not (Test-Path $SourceEa)) { throw "Missing source EA: $SourceEa" }
if (-not (Test-Path $RulesLock)) { throw "Missing locked rules: $RulesLock" }
if (-not (Test-Path $Publisher)) { throw "Missing publisher: $Publisher" }

Step '1/8 Locate exact live FundedNext target'
$dataPath = Find-ExactTarget
$install = Resolve-Install $dataPath
Write-Host "EXPECTED account : $TargetAccount"
Write-Host "EXPECTED server  : $TargetServer"
Write-Host "Target data path : $dataPath"
Write-Host "Source terminal  : $($install.Terminal)"

Prepare-Portable $dataPath $install
$portableTerminal = Join-Path $PortableRoot 'terminal64.exe'
$portableEditor = Join-Path $PortableRoot 'metaeditor64.exe'
if (-not (Test-Path $portableTerminal)) { throw 'Portable terminal64.exe missing after clone.' }
if (-not (Test-Path $portableEditor)) { throw 'Portable metaeditor64.exe missing after clone.' }

Step '3/8 Generate isolated D025 harness'
$expertDir = Join-Path $PortableRoot 'MQL5\Experts\GuardianResearch\Backtests'
$eaBase = "D025_LER_BT_$RunId"
$mq5 = Join-Path $expertDir ($eaBase + '.mq5')
$ex5 = Join-Path $expertDir ($eaBase + '.ex5')
Build-Harness $mq5
Write-Host "Harness: $mq5"

Step '4/8 Compile in portable MetaEditor'
$compileLog = Join-Path $WorkLocal 'compile.log'
Start-Process -FilePath $portableEditor -ArgumentList "/portable /compile:`"$mq5`" /log:`"$compileLog`"" | Out-Null
$compileDeadline=(Get-Date).AddSeconds(120)
while (-not (Test-Path $ex5)) {
    if ((Get-Date) -gt $compileDeadline) {
        $txt = if (Test-Path $compileLog) { Get-Content $compileLog -Raw } else { '(no compile log)' }
        throw "Portable compile did not produce EX5.`n$txt"
    }
    Start-Sleep -Milliseconds 500
}
Start-Sleep -Seconds 1
if (Test-Path $compileLog) {
    $txt = Get-Content $compileLog -Raw
    Write-Host ($txt.Trim())
    if ($txt -match '(?i)([1-9][0-9]*)\s+error') { throw 'Harness compile errors.' }
}

Step '5/8 Launch isolated Strategy Tester'
$ini = Join-Path $WorkLocal 'tester_server2.ini'
$expertRelative = "GuardianResearch\Backtests\$eaBase"
$iniText = @"
[Common]
Login=$TargetAccount
Server=$TargetServer
KeepPrivate=1
NewsEnable=0

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
ShutdownTerminal=1
"@
Set-Content $ini -Value $iniText -Encoding ASCII
Write-Host "Run ID      : $RunId"
Write-Host "Account     : $TargetAccount"
Write-Host "Server      : $TargetServer"
Write-Host "Period      : $FromDate -> $ToDate"
Write-Host "Symbols     : $Symbol1 + $Symbol2"
Write-Host 'Model       : real ticks'
Write-Host 'Live trading: DISABLED'
$proc = Start-Process -FilePath $portableTerminal -ArgumentList "/portable /config:`"$ini`"" -PassThru

Step '6/8 Verify correct portable target and wait for completion'
$verifyDeadline=(Get-Date).AddMinutes(3)
$confirmed=$false
while ((Get-Date) -lt $verifyDeadline -and -not $confirmed) {
    $logs = Join-Path $PortableRoot 'logs'
    if (Test-Path $logs) {
        foreach ($f in @(Get-ChildItem $logs -File -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 4)) {
            $t=Tail $f.FullName 3000
            if (($t -match [regex]::Escape($TargetServer)) -or ($t -match [regex]::Escape($TargetAccount))) { $confirmed=$true; break }
        }
    }
    if (Find-OutputDir) { $confirmed=$true }
    if (-not $confirmed) { Start-Sleep -Seconds 2 }
}
if (-not $confirmed) {
    try { if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force } } catch {}
    throw "Portable clone did not confirm $TargetServer/account $TargetAccount within 3 minutes. Live terminal was untouched."
}
Write-Host "CONFIRMED TARGET: $TargetAccount / $TargetServer" -ForegroundColor Green

$deadline=(Get-Date).AddMinutes($TimeoutMinutes)
$last=(Get-Date)
$outputDir=$null
while ($null -eq $outputDir) {
    $outputDir=Find-OutputDir
    if ($outputDir) { break }
    if ((Get-Date) -gt $deadline) { throw "Backtest timeout after $TimeoutMinutes minutes. Run ID: $RunId" }
    if (((Get-Date)-$last).TotalSeconds -ge 30) {
        Write-Host ("Backtest running... elapsed {0:N1} min" -f ((Get-Date)-$deadline.AddMinutes(-$TimeoutMinutes)).TotalMinutes)
        $last=Get-Date
    }
    Start-Sleep -Seconds 3
}
Write-Host (Get-Content (Join-Path $outputDir 'COMPLETE.txt') -Raw)

Step '7/8 Copy and analyze results'
foreach ($name in @('events.csv','virtual_trades.csv','outcomes.csv','COMPLETE.txt')) {
    $src=Join-Path $outputDir $name
    if (Test-Path $src) { Copy-Item $src (Join-Path $RawLocal $name) -Force }
}
if (-not (Test-Path (Join-Path $RawLocal 'events.csv'))) { throw 'events.csv missing after completion.' }
$terminalBuild=(Get-Item $portableTerminal).VersionInfo.FileVersion
$pubArgs=@(
    '-NoProfile','-ExecutionPolicy','Bypass','-File',$Publisher,
    '-RunId',$RunId,
    '-RawDir',$RawLocal,
    '-PublishDir',$PublishLocal,
    '-FromDate',$FromDate,
    '-ToDate',$ToDate,
    '-HostSymbol',$HostSymbol,
    '-Symbol1',$Symbol1,
    '-Symbol2',$Symbol2,
    '-TerminalBuild',$terminalBuild,
    '-TargetAccount',$TargetAccount,
    '-TargetServer',$TargetServer,
    '-GeneratedHarness',$mq5,
    '-TesterConfig',$ini
)
if ($NoGitHubPush) { $pubArgs += '-NoGitHubPush' }
$p=Start-Process -FilePath 'powershell.exe' -ArgumentList $pubArgs -Wait -PassThru -NoNewWindow
if ($p.ExitCode -ne 0) { throw "Publisher failed with code $($p.ExitCode)." }

Step '8/8 Complete'
Write-Host 'D025 FUNDEDNEXT SERVER2 BACKTEST: COMPLETE' -ForegroundColor Green
Write-Host "Local results : $LocalRoot"
Write-Host "GitHub branch : backtest-results"
Write-Host "Run ID        : $RunId"
Write-Host 'Your live FundedNext terminal/account was never closed.'