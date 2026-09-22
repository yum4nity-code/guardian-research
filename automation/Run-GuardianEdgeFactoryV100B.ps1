param(
  [string]$Root="D:\MT5_Backtests",
  [string]$MetaEditorExe="C:\Program Files\MetaTrader 5\metaeditor64.exe"
)
$ErrorActionPreference="Stop"

$Repo=Join-Path $Root "guardian-research"
$V100=Join-Path $Repo "automation\Run-GuardianEdgeFactoryV100.ps1"
$Py=Join-Path $Repo "scripts\gef_v100b_mql_research_parity.py"
if(!(Test-Path $V100)){throw "Missing $V100"}
if(!(Test-Path $Py)){throw "Missing $Py"}

Write-Host "=== V100B STEP 1/2 - RECOMPILE / RE-AUDIT CURRENT V100.20 ==="
powershell -ExecutionPolicy Bypass -File $V100 -Root $Root -MetaEditorExe $MetaEditorExe
if($LASTEXITCODE -ne 0){throw "V100.20 compile/audit failed"}

py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V100B Python parity compile failed"}

Write-Host "=== V100B STEP 2/2 - PRE-2026 MQL/RESEARCH PARITY ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V100B parity failed"}
