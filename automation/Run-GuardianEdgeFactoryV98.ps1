param(
  [string]$Root="D:\MT5_Backtests",
  [string]$TerminalExe="C:\Program Files\MetaTrader 5\terminal64.exe"
)
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "guardian-research\scripts\gef_v98_ftmo_corrected_bridge.py"
if(!(Test-Path $Py)){throw "Missing $Py"}
if($TerminalExe){$env:GEF_FTMO_TERMINAL=$TerminalExe}
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V98 compile failed"}
Write-Host "=== GEF V98 - CORRECTED RANKS 7/9 FTMO FEED/EXECUTION BRIDGE ==="
py $Py
if($LASTEXITCODE -ne 0){throw "V98 failed"}
