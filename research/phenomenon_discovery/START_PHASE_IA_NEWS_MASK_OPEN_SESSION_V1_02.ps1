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

function Get-SingleOpenMt5 {
    $procs = @(Get-Process terminal64 -ErrorAction SilentlyContinue)
    if ($procs.Count -ne 1) {
        throw "Phase I-A requires exactly one open MT5 terminal64 process. Found: $($procs.Count)."
    }
    $p = $procs[0]
    $exe = $null
    try { $exe = $p.Path } catch {}
    if (-not $exe) { throw "Cannot resolve executable path of the single open MT5 process." }
    $install = Split-Path -Parent $exe
    $editor = Join-Path $install "metaeditor64.exe"
    if (-not (Test-Path -LiteralPath $editor)) { throw "MetaEditor missing beside open MT5: $editor" }

    $cmdline = ""
    try {
        $wmi = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $p.Id) -ErrorAction Stop
        if ($wmi.CommandLine) { $cmdline = [string]$wmi.CommandLine }
    } catch {}

    return [pscustomobject]@{
        ProcessId = $p.Id
        InstallDir = $install
        Terminal = $exe
        Editor = $editor
        CommandLine = $cmdline
    }
}

function Get-CandidateDataDirs($mt5) {
    $set = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    $root = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    if (Test-Path -LiteralPath $root) {
        foreach ($d in @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)) {
            $originFile = Join-Path $d.FullName "origin.txt"
            if (-not (Test-Path -LiteralPath $originFile)) { continue }
            $origin = (Get-Content -LiteralPath $originFile -Raw -ErrorAction SilentlyContinue).Trim()
            if (-not $origin) { continue }
            if ([string]::Equals($origin.TrimEnd('\'),$mt5.InstallDir.TrimEnd('\'),[System.StringComparison]::OrdinalIgnoreCase)) {
                $null = $set.Add($d.FullName)
            }
        }
    }

    $portable = $false
    if ($mt5.CommandLine -match '(?i)(^|\s)/portable(\s|$)') { $portable = $true }
    if ($portable -or (Test-Path -LiteralPath (Join-Path $mt5.InstallDir "MQL5"))) {
        $null = $set.Add($mt5.InstallDir)
    }

    return @($set)
}

function Compile-ExporterInto([string]$DataDir,[string]$Editor,[int]$Index) {
    $scriptDir = Join-Path $DataDir "MQL5\Scripts\Guardian"
    New-Item -ItemType Directory -Force -Path $scriptDir | Out-Null
    $scriptMq5 = Join-Path $scriptDir "ExportNewsCalendarIA.mq5"
    $scriptEx5 = Join-Path $scriptDir "ExportNewsCalendarIA.ex5"
    Copy-Item -LiteralPath $ExporterSource -Destination $scriptMq5 -Force
    if (Test-Path -LiteralPath $scriptEx5) { Remove-Item -LiteralPath $scriptEx5 -Force }

    $compileLog = Join-Path $OutDir ("phase_ia_metaeditor_compile_candidate_" + $Index + ".log")
    if (Test-Path -LiteralPath $compileLog) { Remove-Item -LiteralPath $compileLog -Force }
    $compileArgs = "/compile:`"$scriptMq5`" /log:`"$compileLog`""
    $cp = Start-Process -FilePath $Editor -ArgumentList $compileArgs -Wait -PassThru
    if (-not (Test-Path -LiteralPath $scriptEx5)) {
        $tail = ""
        if (Test-Path -LiteralPath $compileLog) { $tail = (Get-Content -LiteralPath $compileLog -Tail 30) -join "`n" }
        throw "Calendar exporter failed to compile in candidate data dir $DataDir. MetaEditor exit=$($cp.ExitCode). $tail"
    }
    return $scriptEx5
}

function Read-KeyValueManifest([string]$Path) {
    $map = @{}
    foreach ($line in @(Get-Content -LiteralPath $Path -ErrorAction Stop)) {
        $idx = $line.IndexOf('=')
        if ($idx -le 0) { continue }
        $k = $line.Substring(0,$idx).Trim()
        $v = $line.Substring($idx+1).Trim()
        $map[$k] = $v
    }
    return $map
}

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE I-A OPEN SESSION v1.02 ===" -ForegroundColor Cyan
Write-Host "Canonical source: the one and only MT5 session already open."
Write-Host "No second terminal is launched. Candidate data folders are staged only;"
Write-Host "the running MT5 itself proves the real TERMINAL_DATA_PATH when the script executes."
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

    $mt5 = Get-SingleOpenMt5
    Write-Host ("Using sole open MT5 PID " + $mt5.ProcessId + ": " + $mt5.InstallDir) -ForegroundColor Yellow
    if ($mt5.CommandLine) { Write-Host ("Process command line: " + $mt5.CommandLine) }

    $candidates = @(Get-CandidateDataDirs $mt5)
    if ($candidates.Count -eq 0) {
        throw "No candidate MT5 data directory could be associated with the sole open terminal."
    }
    Write-Host ("Candidate data directories: " + $candidates.Count)
    $compiled = @()
    $i = 0
    foreach ($dataDir in $candidates) {
        $i++
        Write-Host ("  staging " + $i + "/" + $candidates.Count + ": " + $dataDir)
        $compiled += Compile-ExporterInto -DataDir $dataDir -Editor $mt5.Editor -Index $i
    }

    foreach ($p in @($RawCommon,$ManifestCommon,$RawLocal,$ManifestLocal)) {
        if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force }
    }

    try {
        $null = Invoke-Python @($Publisher,"--phase","phase-ia-news-mask","--status","RUNNING","--summary","Phase I-A v1.02 staged exporter into all data-folder candidates of the sole open MT5. Waiting for execution in that exact session; no second MT5 launched; 2026 protected.")
    } catch {}

    Write-Host ""
    Write-Host "Exporter is now staged for the OPEN MT5." -ForegroundColor Green
    Write-Host "In MT5: right-click Navigator -> Scripts -> Refresh." -ForegroundColor Yellow
    Write-Host "Then run once: Scripts -> Guardian -> ExportNewsCalendarIA" -ForegroundColor Yellow
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

    $manifest = Read-KeyValueManifest $ManifestLocal
    if (-not $manifest.ContainsKey("terminal_path")) { throw "Exporter manifest is missing terminal_path." }
    if (-not $manifest.ContainsKey("terminal_data_path")) { throw "Exporter manifest is missing terminal_data_path." }
    if (-not [string]::Equals(([string]$manifest["terminal_path"]).TrimEnd('\'),$mt5.InstallDir.TrimEnd('\'),[System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Exporter terminal_path does not match the sole open MT5 installation."
    }
    $realDataDir = [string]$manifest["terminal_data_path"]
    $candidateMatch = $false
    foreach ($d in $candidates) {
        if ([string]::Equals($d.TrimEnd('\'),$realDataDir.TrimEnd('\'),[System.StringComparison]::OrdinalIgnoreCase)) {
            $candidateMatch = $true
            break
        }
    }
    if (-not $candidateMatch) {
        throw "Running MT5 reported TERMINAL_DATA_PATH '$realDataDir', but it was not among staged candidates. Refusing to continue."
    }
    Write-Host ("Canonical TERMINAL_DATA_PATH proven by running MT5: " + $realDataDir) -ForegroundColor Green

    $code = Invoke-Python @($Builder,"--raw-csv",$RawLocal,"--terminal-manifest",$ManifestLocal,"--policy",$Policy,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-A mask build failed, exit=$code" }
    $code = Invoke-Python @($Checker,"--input-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-A integrity gate failed, exit=$code" }

    $Summary = Join-Path $OutDir "phase_ia_summary.json"
    $Integrity = Join-Path $OutDir "phase_ia_integrity.json"
    $Events = Join-Path $OutDir "phase_ia_xauusd_high_impact_events_2024_2025.csv"
    $Mask = Join-Path $OutDir "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    $pubArgs = @($Publisher,"--phase","phase-ia-news-mask","--status","PASS","--summary","Phase I-A v1.02 passed using the sole pre-existing open MT5 session as canonical server/data source. Running terminal self-reported and proved its TERMINAL_DATA_PATH; USD high-impact 2024-2025 XAUUSD +/-5m mask built; no second MT5 launched; 2026 untouched.")
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
