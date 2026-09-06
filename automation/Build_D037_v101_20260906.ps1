param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$repo='D:\MT5_Backtests\guardian-research'
$src=Join-Path $repo 'research\strategies\d037\D037_Williams_M15_v1_00.mq5'
$out=Join-Path $repo 'research\strategies\d037\D037_Williams_M15_v1_01.mq5'
$mt5='D:\MT5_FundedNext\MQL5\Experts\GuardianReasearch\D037_Williams_M15_v1_01.mq5'

if(-not(Test-Path -LiteralPath $src)){throw "SOURCE MISSING: $src"}
$raw=Get-Content -LiteralPath $src -Raw

function Replace-Once([string]$text,[string]$old,[string]$new,[string]$label){
    $count=([regex]::Matches($text,[regex]::Escape($old))).Count
    if($count -ne 1){throw "$label expected once, got $count"}
    return $text.Replace($old,$new)
}

$raw=Replace-Once $raw '#property version "1.00"' '#property version "1.01"' 'property version'
$raw=Replace-Once $raw 'string SOURCE_NAME="D037_Williams_M15_v1_00.mq5";' 'string SOURCE_NAME="D037_Williams_M15_v1_01.mq5";' 'source name'
$raw=Replace-Once $raw 'string SOURCE_VERSION="1.00";' 'string SOURCE_VERSION="1.01";' 'source version'
$raw=$raw.Replace('D037 V100','D037 V101')
$raw=$raw.Replace('D037_V100_','D037_V101_')

$old=@'
      if(CopyRates(_Symbol,PERIOD_M15,0,2,r)>=1)
      {
         MqlRates last=r[0];
         if(last.time!=g_last_processed_bar)
         {
            ProcessClosedBar(last);
            g_last_processed_bar=last.time;
         }
         if(g_fatal_status=="" && g_in_trade)
            WriteTrade(last.time,ClosePx(g_long,last),"TEST_END");
      }
'@
$new=@'
      if(CopyRates(_Symbol,PERIOD_M15,0,3,r)>=2)
      {
         // Only the last CLOSED M15 bar is eligible here. r[0] is the current/forming bar.
         MqlRates last_closed=r[1];
         if(last_closed.time!=g_last_processed_bar)
         {
            ProcessClosedBar(last_closed);
            g_last_processed_bar=last_closed.time;
         }
         if(g_fatal_status=="" && g_in_trade)
            WriteTrade(last_closed.time,ClosePx(g_long,last_closed),"TEST_END");
      }
'@
$raw=Replace-Once $raw $old $new 'OnDeinit closed-bar patch'

if($raw.Contains('D037_Williams_M15_v1_00.mq5')){throw 'old SOURCE_NAME remains'}
if($raw.Contains('D037_V100_')){throw 'old CSV V100 prefix remains'}
if($raw.Contains('MqlRates last=r[0];')){throw 'unsafe OnDeinit r[0] remains'}
if(-not $raw.Contains('MqlRates last_closed=r[1];')){throw 'v1.01 closed-bar fix missing'}

Set-Content -LiteralPath $out -Value $raw -Encoding UTF8
Copy-Item -LiteralPath $out -Destination $mt5 -Force

Write-Host 'CREATED: D037_Williams_M15_v1_01.mq5'
Write-Host 'DEPLOYED TO MT5'
Write-Host 'FIX ONLY: OnDeinit now uses r[1] (last closed bar), never r[0]'
Write-Host 'CSV PREFIX: D037_V101_*'
Write-Host 'NEXT: compile v1.01, then run DEV on the six symbols.'
