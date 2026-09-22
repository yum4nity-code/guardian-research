param(
  [string]$Root="D:\MT5_Backtests",
  [string]$MetaEditorExe="C:\Program Files\MetaTrader 5\metaeditor64.exe"
)
$ErrorActionPreference="Stop"

$Repo=Join-Path $Root "guardian-research"
$Mq5=Join-Path $Repo "mt5\GuardianEdgeForward\GuardianEdgeForward.mq5"
$Py=Join-Path $Repo "scripts\gef_v100_forward_package_audit.py"
if(!(Test-Path $Mq5)){throw "Missing $Mq5"}
if(!(Test-Path $Py)){throw "Missing $Py"}

py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V100 Python audit compile failed"}

$CompileDir=Join-Path $Root "Research\Autonomous\guardian_edge_factory_v100_forward_package"
New-Item -ItemType Directory -Path $CompileDir -Force | Out-Null
$Log=Join-Path $CompileDir "METAEDITOR_V100_COMPILE.log"

if(Test-Path $MetaEditorExe){
  Remove-Item $Log -Force -ErrorAction SilentlyContinue
  Write-Host "=== V100 METAEDITOR COMPILE ==="
  $arg1="/compile:`"$Mq5`""
  $arg2="/log:`"$Log`""
  $p=Start-Process -FilePath $MetaEditorExe -ArgumentList @($arg1,$arg2) -PassThru -Wait
  Start-Sleep -Milliseconds 500
  if(Test-Path $Log){
    Get-Content $Log -Tail 80
    $env:GEF100_COMPILE_LOG=$Log
    $raw=Get-Content $Log -Raw
    if($raw -notmatch "0 errors"){
      throw "V100 MQL5 compile did not report 0 errors. See $Log"
    }
  } else {
    Write-Warning "MetaEditor returned but no compile log was found; Python audit will record NOT_ATTEMPTED."
  }
} else {
  Write-Warning "MetaEditor not found at $MetaEditorExe; source audit will still run."
}

Write-Host "=== GEF V100 - FORWARD SHADOW PACKAGE AUDIT ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V100 audit failed"}
