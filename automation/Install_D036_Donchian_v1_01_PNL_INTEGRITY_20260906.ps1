param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$RepoRoot='D:\MT5_Backtests\guardian-research'
$Source=Join-Path $RepoRoot 'research\strategies\d036\D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5'
$TargetDir='D:\MT5_FundedNext\MQL5\Experts\GuardianReasearch'
$Target=Join-Path $TargetDir 'D036_DonchianTrendBreakout_H1_v1_01_FUNDEDNEXT_PNLINTEGRITY_20260906.mq5'

if(-not(Test-Path -LiteralPath $Source)){throw "Source v1.00 introuvable: $Source"}
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
$raw=Get-Content -LiteralPath $Source -Raw

# Unique source/version identity. Never overwrite v1.00.
$raw=$raw.Replace('#property version "1.00"','#property version "1.01"')
$raw=$raw.Replace('D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5','D036_DonchianTrendBreakout_H1_v1_01_FUNDEDNEXT_PNLINTEGRITY_20260906.mq5')
$raw=$raw.Replace('string SOURCE_VERSION="1.00";','string SOURCE_VERSION="1.01";')

# Dedicated integrity counters / fatal state.
$oldGlobals='long g_invalid_risk=0;`r`nlong g_csv_rows=0;'
$newGlobals='long g_invalid_risk=0;`r`nlong g_pnl_calc_failures=0;`r`nlong g_csv_rows=0;`r`nbool g_fatal_pnl=false;'
if(-not $raw.Contains($oldGlobals)){
    $oldGlobals="long g_invalid_risk=0;`nlong g_csv_rows=0;"
    $newGlobals="long g_invalid_risk=0;`nlong g_pnl_calc_failures=0;`nlong g_csv_rows=0;`nbool g_fatal_pnl=false;"
}
if(-not $raw.Contains($oldGlobals)){throw 'Global-counter anchor not found.'}
$raw=$raw.Replace($oldGlobals,$newGlobals)

# Primary OrderCalcProfit plus exact USD-quote fallback for EURUSD/GBPUSD only.
$oldMoney=@'
bool MoneyPnL(double exit_px,double &pnl)
{
   ENUM_ORDER_TYPE ot=g_long?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   return OrderCalcProfit(ot,_Symbol,1.0,g_entry,exit_px,pnl);
}
'@
$newMoney=@'
bool MoneyPnL(double exit_px,double &pnl)
{
   ENUM_ORDER_TYPE ot=g_long?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   ResetLastError();
   if(OrderCalcProfit(ot,_Symbol,1.0,g_entry,exit_px,pnl))
      return (MathIsValidNumber(pnl));

   int primary_err=GetLastError();

   // Exact one-lot USD-quote fallback, frozen only for EURUSD/GBPUSD.
   // For these symbols account P/L in USD is contract_size * signed price delta.
   if((StringFind(_Symbol,"EURUSD")>=0 || StringFind(_Symbol,"GBPUSD")>=0) && AssetClass()=="FOREX")
   {
      double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
      if(contract>0.0)
      {
         double delta=g_long ? (exit_px-g_entry) : (g_entry-exit_px);
         pnl=contract*delta;
         if(MathIsValidNumber(pnl))
         {
            PrintFormat("D036 V101 PNL FALLBACK | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f | pnl=%.8f",_Symbol,primary_err,g_entry,exit_px,pnl);
            return true;
         }
      }
   }

   PrintFormat("D036 V101 FATAL MoneyPnL failed | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f",_Symbol,primary_err,g_entry,exit_px);
   return false;
}
'@
if(-not $raw.Contains($oldMoney)){throw 'MoneyPnL anchor not found.'}
$raw=$raw.Replace($oldMoney,$newMoney)

# Never silently discard an opened trade.
$oldFail=@'
   double pnl=0.0;
   if(!MoneyPnL(exit_px,pnl) || g_risk_money<=0.0)
   {
      PrintFormat("D036 FATAL trade PnL calc failed | symbol=%s | exit=%s",_Symbol,TimeToString(exit_time,TIME_DATE|TIME_MINUTES));
      ResetTrade();
      return;
   }
'@
$newFail=@'
   double pnl=0.0;
   if(!MoneyPnL(exit_px,pnl) || g_risk_money<=0.0)
   {
      g_pnl_calc_failures++;
      g_fatal_pnl=true;
      PrintFormat("D036 V101 FATAL trade PnL calc failed | symbol=%s | exit=%s",_Symbol,TimeToString(exit_time,TIME_DATE|TIME_MINUTES));
      ResetTrade();
      return;
   }
'@
if(-not $raw.Contains($oldFail)){throw 'WriteTrade failure anchor not found.'}
$raw=$raw.Replace($oldFail,$newFail)

# STATS schema/value observability.
$oldStatsVals='g_stop_exits,g_channel_exits,g_stage_end_exits,g_test_end_exits,g_invalid_risk,g_csv_rows,'
$newStatsVals='g_stop_exits,g_channel_exits,g_stage_end_exits,g_test_end_exits,g_invalid_risk,g_pnl_calc_failures,g_csv_rows,'
if(-not $raw.Contains($oldStatsVals)){throw 'WriteStats values anchor not found.'}
$raw=$raw.Replace($oldStatsVals,$newStatsVals)

$oldHeader='"stop_exits","channel_exits","stage_end_exits","test_end_exits","invalid_risk","csv_trade_rows","symbol"'
$newHeader='"stop_exits","channel_exits","stage_end_exits","test_end_exits","invalid_risk","pnl_calc_failures","csv_trade_rows","symbol"'
if(-not $raw.Contains($oldHeader)){throw 'STATS header anchor not found.'}
$raw=$raw.Replace($oldHeader,$newHeader)

# Stop processing after an unrecoverable PnL failure.
$onTickAnchor='void OnTick()`r`n{`r`n   MqlRates r[];'
$onTickReplacement='void OnTick()`r`n{`r`n   if(g_fatal_pnl) return;`r`n   MqlRates r[];'
if(-not $raw.Contains($onTickAnchor)){
    $onTickAnchor="void OnTick()`n{`n   MqlRates r[];"
    $onTickReplacement="void OnTick()`n{`n   if(g_fatal_pnl) return;`n   MqlRates r[];"
}
if(-not $raw.Contains($onTickAnchor)){throw 'OnTick anchor not found.'}
$raw=$raw.Replace($onTickAnchor,$onTickReplacement)

# A run with unrecoverable PnL failure must never emit a valid FINAL.
$raw=$raw.Replace('   if(g_in_trade)`r`n   {','   if(!g_fatal_pnl && g_in_trade)`r`n   {')
$raw=$raw.Replace('   WriteStats("FINAL");','   WriteStats(g_fatal_pnl ? "FINAL_INVALID_PNL_CALC" : "FINAL");')
$raw=$raw.Replace('PrintFormat("D036 V100 FINAL | stage=%s | symbol=%s | trades=%d | rows=%d | stops=%d | channels=%d",StageName(),_Symbol,g_trades_closed,g_csv_rows,g_stop_exits,g_channel_exits);','PrintFormat("D036 V101 FINAL | stage=%s | symbol=%s | trades=%d | rows=%d | stops=%d | channels=%d | pnl_failures=%d",StageName(),_Symbol,g_trades_closed,g_csv_rows,g_stop_exits,g_channel_exits,g_pnl_calc_failures);')

# Deterministic v1.01 output filenames so v1.00 files remain untouched.
$raw=$raw.Replace('D036_V100_%s_%s_STATS.csv','D036_V101_%s_%s_STATS.csv')
$raw=$raw.Replace('D036_V100_%s_%s_TRADES.csv','D036_V101_%s_%s_TRADES.csv')
$raw=$raw.Replace('D036 V100','D036 V101')

Set-Content -LiteralPath $Target -Value $raw -Encoding UTF8

# Static assertions.
$check=Get-Content -LiteralPath $Target -Raw
foreach($needle in @(
    '#property version "1.01"',
    'string SOURCE_VERSION="1.01";',
    'g_pnl_calc_failures',
    'D036 V101 PNL FALLBACK',
    'FINAL_INVALID_PNL_CALC',
    'D036_V101_%s_%s_STATS.csv',
    'D036_V101_%s_%s_TRADES.csv'
)){
    if(-not $check.Contains($needle)){throw "Generated v1.01 missing assertion: $needle"}
}
if($check.Contains('D036_V100_%s_%s_STATS.csv') -or $check.Contains('D036_V100_%s_%s_TRADES.csv')){throw 'Generated v1.01 still contains V100 output templates.'}

$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash.ToLowerInvariant()
Write-Host "INSTALLE: $Target"
Write-Host "SHA256:   $hash"
Write-Host 'NEXT: compile this NEW v1.01 file in MetaEditor; then rerun only EURUSD and GBPUSD with D036_DEV_2024_2025.'
