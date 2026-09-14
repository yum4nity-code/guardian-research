param(
    [string]$Repo = "D:\MT5_Backtests\guardian-research",
    [string]$Root = "D:\MT5_Backtests\Research\Autonomous",
    [int]$Workers = 8
)

$ErrorActionPreference = "Stop"

$OldScriptName = "r15_dukascopy_xauusd_boundary_export_v1_01.py"
$OldProgress   = Join-Path $Root "progress\R15-DUKASCOPY-BOUNDARY-EXPORT-R2.json"
$SourceCache   = Join-Path $Root "r15_dukascopy_xauusd_v1\payload_cache"
$Inventory     = Join-Path $Root "r15_dukascopy_xauusd_v1\fastfill_inventory.json"

$FastRoot      = Join-Path $Root "xauusd_dukascopy_fastfill_v1"
$FastCache     = Join-Path $FastRoot "payload_cache"
$FastProgress  = Join-Path $Root "progress\R15-XAU-DUKASCOPY-FASTFILL-R1.json"
$FastStdout    = Join-Path $FastRoot "fastfill.stdout.log"
$FastStderr    = Join-Path $FastRoot "fastfill.stderr.log"

$Preflight = Join-Path $Repo "research\autonomous\test_r15_xau_fastfill_union_v1_00.py"
$InventoryScript = Join-Path $Repo "research\autonomous\inventory_r15_xau_cache_before_fastfill_v1_00.py"
$FastfillScript = Join-Path $Repo "research\autonomous\r15_xau_dukascopy_fastfill_v1_00.py"

Set-Location $Repo

foreach ($p in @($OldProgress,$SourceCache,$Preflight,$InventoryScript,$FastfillScript)) {
    if (!(Test-Path $p)) { throw "Required path missing: $p" }
}

New-Item -ItemType Directory -Force -Path $FastRoot,$FastCache,(Split-Path $FastProgress) | Out-Null

Write-Host ""
Write-Host "=== LOCATE OLD SEQUENTIAL DOWNLOADER ===" -ForegroundColor Cyan

$old = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -match [regex]::Escape($OldScriptName) -and
    $_.CommandLine -notmatch "--probe-only"
})

if ($old.Count -gt 1) {
    $old | Select-Object ProcessId,ParentProcessId,CommandLine | Format-List
    throw "More than one old sequential downloader found. Nothing stopped."
}

$fastAlready = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine -match "r15_xau_dukascopy_fastfill_v1_00\.py"
})
if ($fastAlready.Count -gt 0) {
    $fastAlready | Select-Object ProcessId,ParentProcessId,CommandLine | Format-List
    throw "Fastfill is already running. Nothing changed."
}

if ($old.Count -eq 1) {
    $pidToStop = [int]$old[0].ProcessId
    Write-Host "Stopping only PID $pidToStop and its child process tree..." -ForegroundColor Yellow
    & taskkill.exe /PID $pidToStop /T /F | Out-Host
    Start-Sleep -Seconds 2

    $still = @(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match [regex]::Escape($OldScriptName) -and
        $_.CommandLine -notmatch "--probe-only"
    })
    if ($still.Count -ne 0) {
        $still | Select-Object ProcessId,ParentProcessId,CommandLine | Format-List
        throw "Old downloader is still running. Abort before inventory."
    }

    Write-Host "Old sequential downloader stopped." -ForegroundColor Green
}
else {
    Write-Host "No old sequential downloader process found; proceeding from frozen progress file." -ForegroundColor Yellow
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ProgressSnapshot = Join-Path $Root "r15_dukascopy_xauusd_v1\progress_snapshot_before_fastfill_$stamp.json"
Copy-Item $OldProgress $ProgressSnapshot -Force

Write-Host ""
Write-Host "=== DETERMINISTIC PREFLIGHT ===" -ForegroundColor Cyan
& python $Preflight
if ($LASTEXITCODE -ne 0) { throw "Fastfill deterministic preflight FAIL." }

Write-Host ""
Write-Host "=== EXACT CACHE INVENTORY ===" -ForegroundColor Cyan
& python $InventoryScript --cache-dir $SourceCache --progress-file $ProgressSnapshot --output $Inventory
if ($LASTEXITCODE -ne 0) { throw "Cache inventory FAIL." }

$inv = Get-Content $Inventory -Raw | ConvertFrom-Json

Write-Host ""
Write-Host ("Frozen last completed date : " + $inv.last_completed_date) -ForegroundColor Green
Write-Host ("Total weekdays             : " + $inv.total_weekdays)
Write-Host ("Valid original payloads    : " + $inv.valid_payload_count)
Write-Host ("Known old 404/holidays     : " + $inv.known_missing_or_holiday_in_completed_prefix_count)
Write-Host ("EXACT dates still to fetch : " + $inv.to_fetch_count) -ForegroundColor Yellow
Write-Host ("Protected 2026 opened      : " + $inv.protected_2026_opened)

if ([int]$inv.to_fetch_count -le 0) {
    Write-Host "Nothing left to fetch." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "=== START PARALLEL FASTFILL ===" -ForegroundColor Cyan

$Args = @(
    "`"$FastfillScript`"",
    "--inventory", "`"$Inventory`"",
    "--dest-cache", "`"$FastCache`"",
    "--progress-file", "`"$FastProgress`"",
    "--workers", "$Workers"
)

$p = Start-Process -FilePath "python" -ArgumentList $Args -WorkingDirectory $Repo -RedirectStandardOutput $FastStdout -RedirectStandardError $FastStderr -PassThru

Start-Sleep -Seconds 5

if ($p.HasExited) {
    Write-Host "Fastfill exited immediately. ExitCode=$($p.ExitCode)" -ForegroundColor Red
    if (Test-Path $FastStderr) { Get-Content $FastStderr -Tail 100 }
    if (Test-Path $FastStdout) { Get-Content $FastStdout -Tail 100 }
    throw "Fastfill did not remain running."
}

Write-Host "FASTFILL RUNNING" -ForegroundColor Green
Write-Host ("PID                      : " + $p.Id)
Write-Host ("Workers                  : " + $Workers)
Write-Host ("Original cache FROZEN    : " + $SourceCache)
Write-Host ("Separate fastfill cache  : " + $FastCache)
Write-Host ("Inventory                : " + $Inventory)
Write-Host ("Progress                 : " + $FastProgress)
Write-Host ("STDOUT                   : " + $FastStdout)
Write-Host ("STDERR                   : " + $FastStderr)

if (Test-Path $FastProgress) {
    Write-Host ""
    Write-Host "=== INITIAL FASTFILL PROGRESS ===" -ForegroundColor Cyan
    Get-Content $FastProgress -Raw
}
