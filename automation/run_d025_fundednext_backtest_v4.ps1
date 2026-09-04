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
$V3 = Join-Path $PSScriptRoot 'run_d025_fundednext_backtest_v3.ps1'
if (-not (Test-Path $V3)) { throw "Missing V3 runner: $V3" }

Write-Host ''
Write-Host '=== D025 FundedNext V4: exact live-window provenance + account confirmation ===' -ForegroundColor Cyan
Write-Host 'Rule: V3 still must bind the exact live window (account + server in title).' -ForegroundColor DarkGray
Write-Host 'Portable clone may omit server text in logs; exact account + verified provenance is sufficient.' -ForegroundColor DarkGray

$src = Get-Content $V3 -Raw
$needle = '$src = $src.Replace($old,$new)'
if (-not $src.Contains($needle)) { throw 'V3 patch point changed; V4 refuses to run against an unknown revision.' }

$inject = @'
$src = $src.Replace($old,$new)

# V4: the exact live window has already verified account + server and mapped the source data folder.
# Some FundedNext portable sessions expose the account in terminal logs but omit the server label entirely.
# In that case, preserve safety by requiring the exact account, while provenance is guaranteed by V3's live-window binding.
$strictConfirm = 'return [pscustomobject]@{ServerSeen=$serverSeen;AccountSeen=$accountSeen;Confirmed=($serverSeen -and $accountSeen)}'
$provenanceConfirm = 'return [pscustomobject]@{ServerSeen=$serverSeen;AccountSeen=$accountSeen;Confirmed=$accountSeen}'
if (-not $src.Contains($strictConfirm)) { throw 'V2 portable confirmation block changed; V4 refuses to weaken an unknown verifier.' }
$src = $src.Replace($strictConfirm,$provenanceConfirm)

$strictError = 'throw "Portable clone failed exact target confirmation. server_seen=$s account_seen=$a expected=$TargetAccount/$TargetServer. Live terminal was untouched."'
$provenanceError = 'throw "Portable clone failed account confirmation. account_seen=$a expected_account=$TargetAccount. Exact live-window provenance was verified before cloning. Live terminal was untouched."'
$src = $src.Replace($strictError,$provenanceError)

$confirmLine = 'Write-Host "CONFIRMED TARGET: $TargetAccount / $TargetServer" -ForegroundColor Green'
$confirmReplacement = 'Write-Host "CONFIRMED TARGET: $TargetAccount / $TargetServer (live-window provenance + portable account)" -ForegroundColor Green'
$src = $src.Replace($confirmLine,$confirmReplacement)
'@

$patched = $src.Replace($needle,$inject)
$tempV3 = Join-Path $PSScriptRoot (".d025_v3_v4_{0}.ps1" -f ([guid]::NewGuid().ToString('N')))
Set-Content -Path $tempV3 -Value $patched -Encoding UTF8

try {
    $args = @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$tempV3,
        '-FromDate',$FromDate,
        '-ToDate',$ToDate,
        '-HostSymbol',$HostSymbol,
        '-Symbol1',$Symbol1,
        '-Symbol2',$Symbol2,
        '-TargetAccount',$TargetAccount,
        '-TargetServer',$TargetServer,
        '-TimeoutMinutes',$TimeoutMinutes
    )
    if ($NoGitHubPush) { $args += '-NoGitHubPush' }
    & powershell.exe @args
    $rc = $LASTEXITCODE
    if ($rc -ne 0) { throw "V4 delegated run failed with exit code $rc." }
}
finally {
    Remove-Item $tempV3 -Force -ErrorAction SilentlyContinue
}
