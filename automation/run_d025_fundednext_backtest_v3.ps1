param(
    [string]$FromDate = '2025.01.01',
    [string]$ToDate = '2026.06.28',
    [string]$HostSymbol = 'BTCUSD',
    [string]$Symbol1 = 'BTCUSD',
    [string]$Symbol2 = 'ETHUSD',
    [string]$TargetAccount = '14202634',
    [string]$TargetServer = 'FundedNext-Server 2',
    [int]$TimeoutMinutes = 480,
    [switch]$NoGitHubPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$V2 = Join-Path $PSScriptRoot 'run_d025_fundednext_backtest_v2.ps1'
if (-not (Test-Path $V2)) { throw "Missing V2 runner: $V2" }

function Clean([string]$Text) {
    if ($null -eq $Text) { return '' }
    return (($Text -replace "`0", '').Trim())
}

function Normalize-Path([string]$Path) {
    if (-not $Path) { return '' }
    try {
        $p = $Path
        if (Test-Path $p -PathType Leaf) { $p = Split-Path $p -Parent }
        return ([IO.Path]::GetFullPath($p)).TrimEnd('\').ToLowerInvariant()
    } catch { return $Path.TrimEnd('\').ToLowerInvariant() }
}

function Find-LiveTargetProcess {
    $accountRx = [regex]::Escape($TargetAccount)
    $serverRx = [regex]::Escape($TargetServer)
    $hits = @()

    foreach ($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)) {
        $title = ''
        try { $title = $p.MainWindowTitle } catch {}
        if (-not $title) { continue }
        if (($title -match $accountRx) -and ($title -match $serverRx)) {
            $exe = ''
            try { $exe = $p.Path } catch {}
            if (-not $exe) {
                try { $exe = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").ExecutablePath } catch {}
            }
            $hits += [pscustomobject]@{ Id=$p.Id; Title=$title; ExecutablePath=$exe }
        }
    }

    if ($hits.Count -eq 0) {
        Write-Host 'Visible MT5 terminal windows:' -ForegroundColor Yellow
        foreach ($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)) {
            if ($p.MainWindowTitle) { Write-Host ("  PID {0}: {1}" -f $p.Id,$p.MainWindowTitle) }
        }
        throw "No RUNNING MT5 window title contains both account $TargetAccount and server $TargetServer. Keep the correct FundedNext terminal open and retry."
    }
    if ($hits.Count -gt 1) {
        Write-Host 'Matching terminals:' -ForegroundColor Yellow
        $hits | Format-Table Id,Title,ExecutablePath -AutoSize | Out-Host
        throw "More than one running terminal matches $TargetAccount / $TargetServer. Close the duplicate and retry."
    }
    if (-not $hits[0].ExecutablePath) { throw 'Matched the live terminal window but could not resolve its executable path.' }
    return $hits[0]
}

function Find-DataPathFromOrigin([string]$ExecutablePath) {
    $installDir = Normalize-Path (Split-Path $ExecutablePath -Parent)
    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    $matches = @()

    foreach ($d in @(Get-ChildItem $terminalRoot -Directory -ErrorAction SilentlyContinue)) {
        if ($d.Name -eq 'Common') { continue }
        $originFile = Join-Path $d.FullName 'origin.txt'
        if (-not (Test-Path $originFile)) { continue }
        try {
            $origin = Clean (Get-Content $originFile -Raw -ErrorAction Stop)
            $originNorm = Normalize-Path $origin
            if ($originNorm -eq $installDir) {
                $matches += $d.FullName
            }
        } catch {}
    }

    if ($matches.Count -eq 1) { return $matches[0] }

    # Portable terminals use their installation directory as their data directory.
    $rawInstall = Split-Path $ExecutablePath -Parent
    if ((Test-Path (Join-Path $rawInstall 'MQL5')) -and (Test-Path (Join-Path $rawInstall 'config'))) {
        return $rawInstall
    }

    if ($matches.Count -gt 1) {
        Write-Host 'origin.txt candidates tied to this executable:' -ForegroundColor Yellow
        $matches | ForEach-Object { Write-Host "  $_" }
        throw 'Several MT5 data folders map to the same running executable. Refusing to guess.'
    }
    throw "Running target found, but no MT5 data folder origin.txt maps to install directory: $installDir"
}

Write-Host ''
Write-Host '=== D025 FundedNext V3: resolve target from LIVE WINDOW ===' -ForegroundColor Cyan
$live = Find-LiveTargetProcess
$dataPath = Find-DataPathFromOrigin $live.ExecutablePath

Write-Host ("CONFIRMED LIVE WINDOW : PID {0}" -f $live.Id) -ForegroundColor Green
Write-Host ("Title                 : {0}" -f $live.Title)
Write-Host ("Executable            : {0}" -f $live.ExecutablePath)
Write-Host ("Resolved data path    : {0}" -f $dataPath)
Write-Host ("Expected account      : {0}" -f $TargetAccount)
Write-Host ("Expected server       : {0}" -f $TargetServer)

# V2 has a conservative preflight that searches account/server text in files. Some FundedNext
# installations do not persist those strings there. Because V3 has just bound the folder to the
# exact running window, create a temporary V2 copy that accepts this already-verified data path.
$src = Get-Content $V2 -Raw
$old = @'
    if ($TerminalDataPath) {
        if (-not (Test-Path $TerminalDataPath)) { throw "TerminalDataPath missing: $TerminalDataPath" }
        if (-not (Has-ServerEvidence $TerminalDataPath)) { throw "Explicit TerminalDataPath has no evidence for $TargetServer" }
        return (Resolve-Path $TerminalDataPath).Path
    }
'@
$new = @'
    if ($TerminalDataPath) {
        if (-not (Test-Path $TerminalDataPath)) { throw "TerminalDataPath missing: $TerminalDataPath" }
        Write-Host "Using TerminalDataPath verified from exact running MT5 window: $TerminalDataPath"
        return (Resolve-Path $TerminalDataPath).Path
    }
'@
if (-not $src.Contains($old)) { throw 'V2 preflight block changed; V3 refuses to patch an unknown runner revision.' }
$src = $src.Replace($old,$new)

# FundedNext can render the same server with punctuation/spacing differences between the title,
# config and terminal logs (for example "FundedNext-Server 2" vs "FundedNext-Server2").
# Keep strict account+server verification, but compare a normalized alphanumeric server token.
$oldConfirm = @'
function Confirm-PortableTarget {
    $serverRegex = [regex]::Escape($TargetServer)
    $accountRegex = [regex]::Escape($TargetAccount)
    $serverSeen = $false
    $accountSeen = $false
    $logs = Join-Path $PortableRoot 'logs'
    if (Test-Path $logs) {
        foreach ($f in @(Get-ChildItem $logs -File -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 6)) {
            $t = Tail $f.FullName 5000
            if ($t -match $serverRegex) { $serverSeen = $true }
            if ($t -match $accountRegex) { $accountSeen = $true }
        }
    }
    return [pscustomobject]@{ServerSeen=$serverSeen;AccountSeen=$accountSeen;Confirmed=($serverSeen -and $accountSeen)}
}
'@
$newConfirm = @'
function Normalize-ServerToken([string]$Text) {
    if ($null -eq $Text) { return '' }
    return (($Text.ToLowerInvariant()) -replace '[^a-z0-9]','')
}

function Confirm-PortableTarget {
    $targetServerNorm = Normalize-ServerToken $TargetServer
    $accountRegex = [regex]::Escape($TargetAccount)
    $serverSeen = $false
    $accountSeen = $false

    # First inspect the portable terminal window title when available.
    foreach ($p in @(Get-Process terminal64 -ErrorAction SilentlyContinue)) {
        $path = ''
        try { $path = $p.Path } catch {}
        if ($path -and $path.StartsWith($PortableRoot,[System.StringComparison]::OrdinalIgnoreCase)) {
            $title = ''
            try { $title = $p.MainWindowTitle } catch {}
            if ($title -match $accountRegex) { $accountSeen = $true }
            $titleNorm = Normalize-ServerToken $title
            if ($targetServerNorm -and $titleNorm.Contains($targetServerNorm)) { $serverSeen = $true }
        }
    }

    # Also inspect terminal logs, normalizing punctuation/spacing for the server comparison.
    $logs = Join-Path $PortableRoot 'logs'
    if (Test-Path $logs) {
        foreach ($f in @(Get-ChildItem $logs -File -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 10)) {
            $t = Tail $f.FullName 7000
            if ($t -match $accountRegex) { $accountSeen = $true }
            $logNorm = Normalize-ServerToken $t
            if ($targetServerNorm -and $logNorm.Contains($targetServerNorm)) { $serverSeen = $true }
        }
    }
    return [pscustomobject]@{ServerSeen=$serverSeen;AccountSeen=$accountSeen;Confirmed=($serverSeen -and $accountSeen)}
}
'@
if (-not $src.Contains($oldConfirm)) { throw 'V2 portable target verification block changed; V3 refuses to patch an unknown runner revision.' }
$src = $src.Replace($oldConfirm,$newConfirm)

# IMPORTANT: keep the temporary runner inside automation/. V2 resolves RepoRoot from $PSScriptRoot;
# placing the temporary copy in %TEMP% made it look for research/ea under AppData\Local instead of
# D:\MT5_Backtests\guardian-research. The file is removed in finally below.
$tempRunner = Join-Path $PSScriptRoot (".d025_v2_windowbound_{0}.ps1" -f ([guid]::NewGuid().ToString('N')))
Set-Content -Path $tempRunner -Value $src -Encoding UTF8

try {
    $args = @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$tempRunner,
        '-FromDate',$FromDate,
        '-ToDate',$ToDate,
        '-HostSymbol',$HostSymbol,
        '-Symbol1',$Symbol1,
        '-Symbol2',$Symbol2,
        '-TargetAccount',$TargetAccount,
        '-TargetServer',$TargetServer,
        '-TerminalDataPath',$dataPath,
        '-TimeoutMinutes',$TimeoutMinutes
    )
    if ($NoGitHubPush) { $args += '-NoGitHubPush' }
    & powershell.exe @args
    $rc = $LASTEXITCODE
    if ($rc -ne 0) { throw "Window-bound V2 runner failed with exit code $rc." }
}
finally {
    Remove-Item $tempRunner -Force -ErrorAction SilentlyContinue
}
