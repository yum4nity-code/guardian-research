$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ia_v1"
$CommonDir = Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files\Guardian\phase_ia"
$RawCommon = Join-Path $CommonDir "mt5_high_impact_calendar_2024_2025.csv"
$ManifestCommon = Join-Path $CommonDir "mt5_calendar_terminal_manifest.txt"
$RawLocal = Join-Path $OutDir "mt5_high_impact_calendar_2024_2025.csv"
$ManifestLocal = Join-Path $OutDir "mt5_calendar_terminal_manifest.txt"

$ExporterSource = Join-Path $PSScriptRoot "export_mt5_high_impact_calendar_v1_00.mq5"
$Policy = Join-Path $PSScriptRoot "phase_ia_news_policy_v1.json"
$Builder = Join-Path $PSScriptRoot "build_propfirm_news_mask_v1_00.py"
$Checker = Join-Path $PSScriptRoot "check_propfirm_news_mask_v1_00.py"
$Publisher = Join-Path $PSScriptRoot "publish_phase_result_v1_00.py"

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python 3 not found."
}

function Invoke-Python([string[]]$Arguments) {
    $cmd = Find-Python
    $exe = $cmd[0]
    $prefix = @()
    if ($cmd.Count -gt 1) { $prefix = $cmd[1..($cmd.Count-1)] }
    & $exe @prefix @Arguments | Out-Host
    return [int]$LASTEXITCODE
}

function Get-Mt5Candidates {
    $root = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    if (-not (Test-Path -LiteralPath $root)) { return @() }
    $running = @{}
    foreach ($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)) {
        try {
            if ($p.Path) { $running[$p.Path.ToLowerInvariant()] = $true }
        } catch {}
    }
    $items = @()
    foreach ($d in @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)) {
        $originFile = Join-Path $d.FullName "origin.txt"
        if (-not (Test-Path -LiteralPath $originFile)) { continue }
        $install = (Get-Content -LiteralPath $originFile -Raw -ErrorAction SilentlyContinue).Trim()
        if (-not $install) { continue }
        $terminal = Join-Path $install "terminal64.exe"
        $editor = Join-Path $install "metaeditor64.exe"
        if (-not (Test-Path -LiteralPath $terminal)) { continue }
        if (-not (Test-Path -LiteralPath $editor)) { continue }
        $isRunning = $running.ContainsKey($terminal.ToLowerInvariant())
        $score = 10
        if ($install -match "(?i)FundedNext") { $score = 0 }
        elseif ($install -match "(?i)FTMO") { $score = 1 }
        elseif ($install -match "(?i)MetaTrader") { $score = 5 }
        $items += [pscustomobject]@{
            DataDir = $d.FullName
            InstallDir = $install
            Terminal = $terminal
            Editor = $editor
            IsRunning = $isRunning
            Score = $score
        }
    }
    return @($items | Sort-Object Score, InstallDir)
}

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE I-A ===" -ForegroundColor Cyan
Write-Host "Historical prop-firm news mask for XAUUSD."
Write-Host "Source: MT5 economic calendar, high-impact USD events, 2024-2025 only."
Write-Host "Research exclusion: 5 minutes before through 5 minutes after each event."
Write-Host "The launcher refuses to touch an MT5 installation that is already running."
Write-Host "2026 remains protected."
Write-Host ""

try {
    foreach ($p in @($ExporterSource,$Policy,$Builder,$Checker,$Publisher)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Missing Phase I-A dependency: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    New-Item -ItemType Directory -Force -Path $CommonDir | Out-Null

    $code = Invoke-Python @("-m","py_compile",$Builder,$Checker,$Publisher)
    if ($code -ne 0) { throw "Phase I-A Python preflight failed, exit=$code" }

    $candidates = @(Get-Mt5Candidates)
    if ($candidates.Count -eq 0) { throw "No usable MT5 installation/data directory found via origin.txt." }
    $inactive = @($candidates | Where-Object { -not $_.IsRunning })
    if ($inactive.Count -eq 0) {
        throw "All discovered MT5 installations are currently running. Phase I-A will not interfere with a live terminal. Close one MT5 instance and rerun this same launcher."
    }
    $mt5 = $inactive[0]
    Write-Host ("Selected inactive MT5: " + $mt5.InstallDir) -ForegroundColor Yellow
    Write-Host ("Data directory: " + $mt5.DataDir)

    $scriptDir = Join-Path $mt5.DataDir "MQL5\Scripts\Guardian"
    New-Item -ItemType Directory -Force -Path $scriptDir | Out-Null
    $scriptMq5 = Join-Path $scriptDir "ExportNewsCalendarIA.mq5"
    $scriptEx5 = Join-Path $scriptDir "ExportNewsCalendarIA.ex5"
    Copy-Item -LiteralPath $ExporterSource -Destination $scriptMq5 -Force
    if (Test-Path -LiteralPath $scriptEx5) { Remove-Item -LiteralPath $scriptEx5 -Force }

    $compileLog = Join-Path $OutDir "phase_ia_metaeditor_compile.log"
    if (Test-Path -LiteralPath $compileLog) { Remove-Item -LiteralPath $compileLog -Force }
    $compileArgs = "/compile:`"$scriptMq5`" /log:`"$compileLog`""
    $cp = Start-Process -FilePath $mt5.Editor -ArgumentList $compileArgs -Wait -PassThru
    if (-not (Test-Path -LiteralPath $scriptEx5)) {
        $tail = ""
        if (Test-Path -LiteralPath $compileLog) { $tail = (Get-Content -LiteralPath $compileLog -Tail 30) -join "`n" }
        throw "MT5 calendar exporter did not compile. MetaEditor exit=$($cp.ExitCode). $tail"
    }

    foreach ($p in @($RawCommon,$ManifestCommon,$RawLocal,$ManifestLocal)) {
        if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force }
    }

    try {
        $null = Invoke-Python @($Publisher,"--phase","phase-ia-news-mask","--status","RUNNING","--summary","Phase I-A exporting 2024-2025 MT5 high-impact calendar and building conservative XAUUSD news mask. 2026 protected.")
    } catch {}

    $configPath = Join-Path $OutDir "phase_ia_mt5_startup.ini"
    @"
[Common]
NewsEnable=1

[Experts]
AllowLiveTrading=0
AllowDllImport=0
Enabled=1
Account=0
Profile=0

[StartUp]
Symbol=EURUSD
Period=M1
Script=Guardian\ExportNewsCalendarIA
ShutdownTerminal=1
"@ | Set-Content -LiteralPath $configPath -Encoding ASCII

    Write-Host "Launching isolated service run of the selected inactive MT5..."
    $tp = Start-Process -FilePath $mt5.Terminal -ArgumentList "/config:`"$configPath`"" -PassThru
    $deadline = (Get-Date).AddMinutes(5)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path -LiteralPath $RawCommon) -and (Test-Path -LiteralPath $ManifestCommon)) {
            try {
                if ($tp.HasExited) { break }
            } catch { break }
        }
        Start-Sleep -Seconds 2
    }

    $stillRunning = $false
    try { $stillRunning = -not $tp.HasExited } catch {}
    if ($stillRunning) {
        try { Stop-Process -Id $tp.Id -Force -ErrorAction SilentlyContinue } catch {}
        throw "Phase I-A MT5 calendar export exceeded 5 minutes and was stopped."
    }
    if (-not (Test-Path -LiteralPath $RawCommon)) { throw "MT5 exporter finished without producing the calendar CSV." }
    if (-not (Test-Path -LiteralPath $ManifestCommon)) { throw "MT5 exporter finished without producing the terminal manifest." }

    Copy-Item -LiteralPath $RawCommon -Destination $RawLocal -Force
    Copy-Item -LiteralPath $ManifestCommon -Destination $ManifestLocal -Force

    $code = Invoke-Python @($Builder,"--raw-csv",$RawLocal,"--terminal-manifest",$ManifestLocal,"--policy",$Policy,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-A mask build failed, exit=$code" }
    $code = Invoke-Python @($Checker,"--input-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-A integrity gate failed, exit=$code" }

    $Summary = Join-Path $OutDir "phase_ia_summary.json"
    $Integrity = Join-Path $OutDir "phase_ia_integrity.json"
    $Events = Join-Path $OutDir "phase_ia_xauusd_high_impact_events_2024_2025.csv"
    $Mask = Join-Path $OutDir "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    $pubArgs = @($Publisher,"--phase","phase-ia-news-mask","--status","PASS","--summary","Phase I-A passed. Same-terminal MT5 high-impact USD calendar normalized for 2024-2025; XAUUSD conservative +/-5m mask built and integrity-checked; 2026 untouched; live prop-firm promotion remains fail-closed.")
    foreach ($p in @($Summary,$Integrity,$Events,$Mask,$ManifestLocal,$Policy)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase I-A passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE I-A COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try { $null = Invoke-Python @($Publisher,"--phase","phase-ia-news-mask","--status","FAIL","--summary",$message) } catch {}
    exit 1
}
