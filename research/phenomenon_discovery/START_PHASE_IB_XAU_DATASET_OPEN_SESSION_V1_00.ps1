$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$OutDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1"
$IaDir = "D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ia_v1"
$CommonDir = Join-Path $env:APPDATA "MetaQuotes\Terminal\Common\Files\Guardian\phase_ib"

$RawM1Common = Join-Path $CommonDir "xauusd_m1_2024_2025_raw.csv"
$RawM5Common = Join-Path $CommonDir "xauusd_m5_2024_2025_raw.csv"
$ManifestCommon = Join-Path $CommonDir "xauusd_history_terminal_manifest.txt"
$RawM1Local = Join-Path $OutDir "xauusd_m1_2024_2025_raw.csv"
$RawM5Local = Join-Path $OutDir "xauusd_m5_2024_2025_raw.csv"
$ManifestLocal = Join-Path $OutDir "xauusd_history_terminal_manifest.txt"

$IaSummary = Join-Path $IaDir "phase_ia_summary.json"
$IaMask = Join-Path $IaDir "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
$ExporterSource = Join-Path $PSScriptRoot "export_mt5_xau_history_v1_00.mq5"
$Builder = Join-Path $PSScriptRoot "build_xau_news_clean_dataset_v1_00.py"
$Checker = Join-Path $PSScriptRoot "check_xau_news_clean_dataset_v1_00.py"
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
        throw "Phase I-B requires exactly one open MT5 terminal64 process. Found: $($procs.Count)."
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

    if ($mt5.CommandLine -match '(?i)(^|\s)/portable(\s|$)') {
        $null = $set.Add($mt5.InstallDir)
    } elseif (Test-Path -LiteralPath (Join-Path $mt5.InstallDir "MQL5")) {
        $null = $set.Add($mt5.InstallDir)
    }
    return @($set)
}

function Compile-ExporterInto([string]$DataDir,[string]$Editor,[int]$Index) {
    $scriptDir = Join-Path $DataDir "MQL5\Scripts\Guardian"
    New-Item -ItemType Directory -Force -Path $scriptDir | Out-Null
    $scriptMq5 = Join-Path $scriptDir "ExportXAUHistoryIB.mq5"
    $scriptEx5 = Join-Path $scriptDir "ExportXAUHistoryIB.ex5"
    Copy-Item -LiteralPath $ExporterSource -Destination $scriptMq5 -Force
    if (Test-Path -LiteralPath $scriptEx5) { Remove-Item -LiteralPath $scriptEx5 -Force }

    $compileLog = Join-Path $OutDir ("phase_ib_metaeditor_compile_candidate_" + $Index + ".log")
    if (Test-Path -LiteralPath $compileLog) { Remove-Item -LiteralPath $compileLog -Force }
    $compileArgs = "/compile:`"$scriptMq5`" /log:`"$compileLog`""
    $cp = Start-Process -FilePath $Editor -ArgumentList $compileArgs -Wait -PassThru
    if (-not (Test-Path -LiteralPath $scriptEx5)) {
        $tail = ""
        if (Test-Path -LiteralPath $compileLog) { $tail = (Get-Content -LiteralPath $compileLog -Tail 40) -join "`n" }
        throw "XAU history exporter failed to compile in candidate data dir $DataDir. MetaEditor exit=$($cp.ExitCode). $tail"
    }
}

function Read-KeyValueManifest([string]$Path) {
    $map = @{}
    foreach ($line in @(Get-Content -LiteralPath $Path -ErrorAction Stop)) {
        $idx = $line.IndexOf('=')
        if ($idx -le 0) { continue }
        $map[$line.Substring(0,$idx).Trim()] = $line.Substring($idx+1).Trim()
    }
    return $map
}

Write-Host ""
Write-Host "=== GUARDIAN PHENOMENON DISCOVERY - PHASE I-B XAU DATA GATE ===" -ForegroundColor Cyan
Write-Host "Canonical source: the one and only MT5 session already open."
Write-Host "Export: XAUUSD M1 + M5, 2024-2025 only, from the same server/data path as Phase I-A."
Write-Host "Then apply the frozen USD high-impact +/-5m Phase I-A mask before research use."
Write-Host "No second terminal is launched. 2026 remains sealed."
Write-Host ""

try {
    foreach ($p in @($IaSummary,$IaMask,$ExporterSource,$Builder,$Checker,$Publisher)) {
        if (-not (Test-Path -LiteralPath $p)) { throw "Missing Phase I-B dependency: $p" }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    New-Item -ItemType Directory -Force -Path $CommonDir | Out-Null

    $code = Invoke-Python @("-m","py_compile",$Builder,$Checker,$Publisher)
    if ($code -ne 0) { throw "Phase I-B Python preflight failed, exit=$code" }

    $mt5 = Get-SingleOpenMt5
    Write-Host ("Using sole open MT5 PID " + $mt5.ProcessId + ": " + $mt5.InstallDir) -ForegroundColor Yellow
    if ($mt5.CommandLine) { Write-Host ("Process command line: " + $mt5.CommandLine) }

    $ia = Get-Content -LiteralPath $IaSummary -Raw | ConvertFrom-Json
    if (-not [string]::Equals(([string]$ia.terminal_manifest.terminal_path).TrimEnd('\'),$mt5.InstallDir.TrimEnd('\'),[System.StringComparison]::OrdinalIgnoreCase)) {
        throw "The sole open MT5 installation does not match the canonical Phase I-A terminal_path."
    }

    $candidates = @(Get-CandidateDataDirs $mt5)
    if ($candidates.Count -eq 0) { throw "No data-folder candidates found for the sole open MT5." }
    Write-Host ("Candidate data directories: " + $candidates.Count)
    $i=0
    foreach ($dataDir in $candidates) {
        $i++
        Write-Host ("  staging " + $i + "/" + $candidates.Count + ": " + $dataDir)
        Compile-ExporterInto -DataDir $dataDir -Editor $mt5.Editor -Index $i
    }

    foreach ($p in @($RawM1Common,$RawM5Common,$ManifestCommon,$RawM1Local,$RawM5Local,$ManifestLocal)) {
        if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force }
    }

    try {
        $null = Invoke-Python @($Publisher,"--phase","phase-ib-xau-dataset","--status","RUNNING","--summary","Phase I-B staged XAUUSD M1/M5 exporter into the sole open MT5. Waiting for execution in that exact session; Phase I-A +/-5m mask will be applied before research use; 2026 protected.")
    } catch {}

    Write-Host ""
    Write-Host "Exporter is staged in the OPEN MT5." -ForegroundColor Green
    Write-Host "In MT5: right-click Navigator -> Scripts -> Refresh." -ForegroundColor Yellow
    Write-Host "Then run once: Scripts -> Guardian -> ExportXAUHistoryIB" -ForegroundColor Yellow
    Write-Host "The export can take a few minutes; this PowerShell window will finish automatically." -ForegroundColor Yellow
    Write-Host ""

    $deadline = (Get-Date).AddMinutes(20)
    while ((Get-Date) -lt $deadline) {
        $same = @(Get-Process terminal64 -ErrorAction SilentlyContinue)
        if ($same.Count -ne 1 -or $same[0].Id -ne $mt5.ProcessId) {
            throw "Canonical MT5 session changed while Phase I-B was waiting. Refusing to continue."
        }
        if ((Test-Path -LiteralPath $RawM1Common) -and (Test-Path -LiteralPath $RawM5Common) -and (Test-Path -LiteralPath $ManifestCommon)) { break }
        Start-Sleep -Seconds 3
    }
    if (-not (Test-Path -LiteralPath $RawM1Common)) { throw "Timed out waiting for XAUUSD M1 export from the canonical open MT5." }
    if (-not (Test-Path -LiteralPath $RawM5Common)) { throw "Timed out waiting for XAUUSD M5 export from the canonical open MT5." }
    if (-not (Test-Path -LiteralPath $ManifestCommon)) { throw "XAU history files appeared without terminal manifest; refusing to continue." }

    Copy-Item -LiteralPath $RawM1Common -Destination $RawM1Local -Force
    Copy-Item -LiteralPath $RawM5Common -Destination $RawM5Local -Force
    Copy-Item -LiteralPath $ManifestCommon -Destination $ManifestLocal -Force

    $manifest = Read-KeyValueManifest $ManifestLocal
    if (-not $manifest.ContainsKey("terminal_path") -or -not $manifest.ContainsKey("terminal_data_path") -or -not $manifest.ContainsKey("server")) {
        throw "I-B exporter manifest is incomplete."
    }
    if (-not [string]::Equals(([string]$manifest["terminal_path"]).TrimEnd('\'),$mt5.InstallDir.TrimEnd('\'),[System.StringComparison]::OrdinalIgnoreCase)) {
        throw "I-B exporter terminal_path does not match the sole open MT5."
    }
    if (-not [string]::Equals(([string]$manifest["terminal_data_path"]).TrimEnd('\'),([string]$ia.terminal_manifest.terminal_data_path).TrimEnd('\'),[System.StringComparison]::OrdinalIgnoreCase)) {
        throw "I-B TERMINAL_DATA_PATH does not match Phase I-A canonical path."
    }
    if (-not [string]::Equals(([string]$manifest["server"]),([string]$ia.terminal_manifest.server),[System.StringComparison]::Ordinal)) {
        throw "I-B server does not match Phase I-A canonical server."
    }
    Write-Host ("Canonical server/path confirmed: " + $manifest["server"] + " / " + $manifest["terminal_data_path"]) -ForegroundColor Green

    $code = Invoke-Python @($Builder,"--raw-m1",$RawM1Local,"--raw-m5",$RawM5Local,"--ib-terminal-manifest",$ManifestLocal,"--ia-summary",$IaSummary,"--ia-mask",$IaMask,"--output-dir",$OutDir)
    if ($code -ne 0) { throw "Phase I-B news-clean dataset build failed, exit=$code" }
    $code = Invoke-Python @($Checker,"--input-dir",$OutDir,"--ia-mask",$IaMask)
    if ($code -ne 0) { throw "Phase I-B integrity gate failed, exit=$code" }

    $Summary = Join-Path $OutDir "phase_ib_summary.json"
    $Integrity = Join-Path $OutDir "phase_ib_integrity.json"
    $Audit = Join-Path $OutDir "phase_ib_news_exclusion_audit.csv"
    $pubArgs = @($Publisher,"--phase","phase-ib-xau-dataset","--status","PASS","--summary","Phase I-B PASS. XAUUSD M1/M5 2024-2025 exported from the exact same sole-open FundedNext MT5 server/data path as Phase I-A; conservative USD high-impact +/-5m news mask applied before research use; integrity checked; 2026 untouched.")
    foreach ($p in @($Summary,$Integrity,$Audit,$ManifestLocal)) {
        if (Test-Path -LiteralPath $p) { $pubArgs += @("--artifact",$p) }
    }
    $pubCode = Invoke-Python $pubArgs
    if ($pubCode -ne 0) { throw "Phase I-B passed locally but publication failed, exit=$pubCode" }

    Write-Host ""
    Write-Host "=== PHASE I-B COMPLETE AND PUBLISHED ===" -ForegroundColor Green
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Error $message
    try { $null = Invoke-Python @($Publisher,"--phase","phase-ib-xau-dataset","--status","FAIL","--summary",$message) } catch {}
    exit 1
}
