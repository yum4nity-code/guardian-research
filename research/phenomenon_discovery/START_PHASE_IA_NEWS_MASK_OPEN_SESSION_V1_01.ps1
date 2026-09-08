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

function Resolve-OpenMt5 {
    $procs = @(Get-Process terminal64 -ErrorAction SilentlyContinue)
    if ($procs.Count -ne 1) {
        throw "Phase I-A requires exactly one open MT5 terminal64 process. Found: $($procs.Count)."
    }
    $p = $procs[0]
    $exe = $null
    try { $exe = $p.Path } catch {}
    if (-not $exe) { throw "Cannot resolve executable path of the single open MT5 process." }
    $install = Split-Path -Parent $exe

    $root = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    $matches = @()
    foreach ($d in @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)) {
        $originFile = Join-Path $d.FullName "origin.txt"
        if (-not (Test-Path -LiteralPath $originFile)) { continue }
        $origin = (Get-Content -LiteralPath $originFile -Raw -ErrorAction SilentlyContinue).Trim()
        if ($origin -and ([string]::Equals($origin.TrimEnd('\\'),$install.TrimEnd('\\'),[System.StringComparison]::OrdinalIgnoreCase))) {
            $matches += $d.FullName
        }
    }
    if ($matches.Count -ne 1) {
        throw "Could not map the single open MT5 installation to exactly one data directory via origin.txt. Matches: $($matches.Count)."
    }
    $editor = Join-Path $install "metaeditor64.exe"
    if (-not (Test-Path -LiteralPath $editor)) { throw "MetaEditor missing beside open MT5: $editor" }

    return [pscustomobject]@{
        ProcessId = $p.Id
        InstallDir = $install
        Terminal = $exe
        Editor = $editor
        DataDir = $matches[0]
    }
}

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE I-A OPEN SESSION ===" -ForegroundColor Cyan
Write-Host "Canonical source: the one and only MT5 session already open."
Write-Host "No second terminal is launched. 2026 remains protected."
Write-Host ""

try {
    foreach ($p in @($ExporterSource,$Policy,$Builder,$Checker,$Publisher)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Missing Phase I-A dependency: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    New-Item -ItemType Directory -Force -Path $CommonDir | Out-Null

    $code = Invoke-Python @("-m","py_compile",$Builder,$Checker,$Publisher)
    if ($code -ne 0) { throw "Phase I-A Python preflight failed, exit=$code" }

    $mt5 = Resolve-OpenMt5
    Write-Host ("Using open MT5 PID " + $mt5.ProcessId + ": " + $mt5.InstallDir) -ForegroundColor Yellow
    Write-Host ("Canonical data directory: " + $mt5.DataDir)

    $scriptDir = Join-Path $mt5.DataDir "MQL5\Scripts\Guardian"
    New-Item -ItemType Directory -Force -Path $scriptDir | Out-Null
    $scriptMq5 = Join-Path $scriptDir "ExportNewsCalendarIA.mq5"
    $scriptEx5 = Join-Path $scriptDir "ExportNewsCalendarIA.ex5"
    Copy-Item -LiteralPath $ExporterSource -Destination $scriptMq5 -Force
    if (Test-Path -LiteralPath $scriptEx5) { Remove-Item -LiteralPath $scriptEx5 -Force }

    $compileLog = Join-Path $OutDir "phase_ia_metaeditor_compile_open_session.log"
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
        $null = Invoke-Python @($Publisher,"--phase","phase-ia-news-mask","--status","RUNNING","--summary","Phase I-A open-session mode prepared on the sole running MT5. Waiting for Guardian\\ExportNewsCalendarIA to execute in that exact terminal. No second MT5 launched; 2026 protected.")
    } catch {}

    Write-Host ""
    Write-Host "Exporter compiled into the OPEN MT5 session." -ForegroundColor Green
    Write-Host "In that MT5, run once: Navigator -> Scripts -> Guardian -> ExportNewsCalendarIA" -ForegroundColor Yellow
    Write-Host "This PowerShell window will detect the output and finish automatically." -ForegroundColor Yellow
    Write-Host ""

    $deadline = (Get-Date).AddMinutes(10)
    while ((Get-Date) -lt $deadline) {
        $same = @(Get-Process terminal64 -ErrorAction SilentlyContinue)
        if ($same.Count -ne 1 -or $same[0].Id -ne $mt5.ProcessId) {
            throw "Canonical MT5 session changed while Phase I-A was waiting. Refusing to continue."
        }
        if ((Test-Path -LiteralPath $RawCommon) -and (Test-Path -LiteralPath $ManifestCommon)) { break }
        Start-Sleep -Seconds 2
    }
    if (-not (Test-Path -LiteralPath $RawCommon)) { throw "Timed out waiting for the calendar export from the canonical open MT5 session." }
    if (-not (Test-Path -LiteralPath $ManifestCommon)) { throw "Calendar CSV appeared without terminal manifest; refusing to continue." }

    Copy-Item -LiteralPath $RawCommon -Destination $RawLocal -Force
    Copy-Item -LiteralPath $ManifestCommon -Destination $ManifestLocal -Force

    $manifestText = Get-Content -LiteralPath $ManifestLocal -Raw
    if ($manifestText -notmatch [regex]::Escape($mt5.DataDir)) {
        throw "Exporter manifest data path does not match canonical open MT5 data directory."
    }

    $code = Invoke-Python @($Builder,"--raw-csv",$RawLocal,"--terminal-manifest",$ManifestLocal,"--policy",$Policy,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-A mask build failed, exit=$code" }
    $code = Invoke-Python @($Checker,"--input-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-A integrity gate failed, exit=$code" }

    $Summary = Join-Path $OutDir "phase_ia_summary.json"
    $Integrity = Join-Path $OutDir "phase_ia_integrity.json"
    $Events = Join-Path $OutDir "phase_ia_xauusd_high_impact_events_2024_2025.csv"
    $Mask = Join-Path $OutDir "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    $pubArgs = @($Publisher,"--phase","phase-ia-news-mask","--status","PASS","--summary","Phase I-A passed using the sole pre-existing open MT5 session as canonical server/data source. USD high-impact 2024-2025 XAUUSD +/-5m research mask built; no second MT5 launched; 2026 untouched.")
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
