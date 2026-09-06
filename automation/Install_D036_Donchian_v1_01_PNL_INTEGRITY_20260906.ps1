param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$RepoRoot='D:\MT5_Backtests\guardian-research'
$Source=Join-Path $RepoRoot 'research\strategies\d036\D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5'
$TargetDir='D:\MT5_FundedNext\MQL5\Experts\GuardianReasearch'
$Target=Join-Path $TargetDir 'D036_DonchianTrendBreakout_H1_v1_01_FUNDEDNEXT_PNLINTEGRITY_20260906.mq5'

if(-not(Test-Path -LiteralPath $Source)){throw "Source v1.00 introuvable: $Source"}
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

# Normalize the committed source to LF first so every multiline patch is deterministic
# regardless of git autocrlf / Windows checkout behavior.
$raw=(Get-Content -LiteralPath $Source -Raw) -replace "`r`n","`n"

function Replace-Exact([string]$Text,[string]$Old,[string]$New,[string]$Label){
    if(-not $Text.Contains($Old)){throw "Patch anchor not found: $Label"}
    return $Text.Replace($Old,$New)
}

# Unique source/version identity. Never overwrite v1.00.
$raw=Replace-Exact $raw '#property version "1.00"' '#property version "1.01"' 'property version'
$raw=Replace-Exact $raw 'D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5' 'D036_DonchianTrendBreakout_H1_v1_01_FUNDEDNEXT_PNLINTEGRITY_20260906.mq5' 'source name'
$raw=Replace-Exact $raw 'string SOURCE_VERSION="1.00";' 'string SOURCE_VERSION="1.01";' 'source version'

# Dedicated integrity counters / fatal state.
$oldGlobals=@'
long g_invalid_risk=0;
long g_csv_rows=0;
'@
$newGlobals=@'
long g_invalid_risk=0;
long g_pnl_fallbacks=0;
long g_pnl_calc_failures=0;
long g_csv_rows=0;
bool g_fatal_pnl=false;
'@
$raw=Replace-Exact $raw $oldGlobals $newGlobals 'global integrity counters'

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
      return MathIsValidNumber(pnl);

   int primary_err=GetLastError();

   // Exact one-lot USD-quote fallback, frozen only for EURUSD/GBPUSD.
   // For these two symbols the quote currency is USD, therefore account P/L in USD
   // is contract_size * signed(exit-entry) for one lot.
   if((StringFind(_Symbol,"EURUSD")>=0 || StringFind(_Symbol,"GBPUSD")>=0) && AssetClass()=="FOREX")
   {
      double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
      if(contract>0.0)
      {
         double delta=g_long ? (exit_px-g_entry) : (g_entry-exit_px);
         pnl=contract*delta;
         if(MathIsValidNumber(pnl))
         {
            g_pnl_fallbacks++;
            PrintFormat("D036 V101 PNL FALLBACK | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f | pnl=%.8f",_Symbol,primary_err,g_entry,exit_px,pnl);
            return true;
         }
      }
   }

   PrintFormat("D036 V101 FATAL MoneyPnL failed | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f",_Symbol,primary_err,g_entry,exit_px);
   return false;
}
'@
$raw=Replace-Exact $raw $oldMoney $newMoney 'MoneyPnL'

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
$raw=Replace-Exact $raw $oldFail $newFail 'WriteTrade failure handling'

# STATS schema/value observability.
$raw=Replace-Exact $raw \
'g_stop_exits,g_channel_exits,g_stage_end_exits,g_test_end_exits,g_invalid_risk,g_csv_rows,' \
'g_stop_exits,g_channel_exits,g_stage_end_exits,g_test_end_exits,g_invalid_risk,g_pnl_fallbacks,g_pnl_calc_failures,g_csv_rows,' \
'WriteStats integrity values'

$raw=Replace-Exact $raw \
'"stop_exits","channel_exits","stage_end_exits","test_end_exits","invalid_risk","csv_trade_rows","symbol"' \
'"stop_exits","channel_exits","stage_end_exits","test_end_exits","invalid_risk","pnl_fallbacks","pnl_calc_failures","csv_trade_rows","symbol"' \
'STATS integrity header'

# Stop processing after an unrecoverable PnL failure.
$oldTick=@'
void OnTick()
{
   MqlRates r[];
'@
$newTick=@'
void OnTick()
{
   if(g_fatal_pnl) return;
   MqlRates r[];
'@
$raw=Replace-Exact $raw $oldTick $newTick 'OnTick fatal guard'

# A run with unrecoverable PnL failure must never emit a valid FINAL.
$oldDeinit=@'
void OnDeinit(const int reason)
{
   if(g_in_trade)
   {
'@
$newDeinit=@'
void OnDeinit(const int reason)
{
   if(!g_fatal_pnl && g_in_trade)
   {
'@
$raw=Replace-Exact $raw $oldDeinit $newDeinit 'OnDeinit fatal guard'
$raw=Replace-Exact $raw '   WriteStats("FINAL");' '   WriteStats(g_fatal_pnl ? "FINAL_INVALID_PNL_CALC" : "FINAL");' 'FINAL validity status'

# Deterministic v1.01 output filenames so v1.00 files remain untouched.
$raw=Replace-Exact $raw 'D036_V100_%s_%s_STATS.csv' 'D036_V101_%s_%s_STATS.csv' 'stats filename template'
$raw=Replace-Exact $raw 'D036_V100_%s_%s_TRADES.csv' 'D036_V101_%s_%s_TRADES.csv' 'trades filename template'
$raw=$raw.Replace('D036 V100','D036 V101')

Set-Content -LiteralPath $Target -Value $raw -Encoding UTF8

# Static assertions before handing the file to MetaEditor.
$check=(Get-Content -LiteralPath $Target -Raw) -replace "`r`n","`n"
foreach($needle in @(
    '#property version "1.01"',
    'string SOURCE_VERSION="1.01";',
    'g_pnl_fallbacks',
    'g_pnl_calc_failures',
    'D036 V101 PNL FALLBACK',
    'FINAL_INVALID_PNL_CALC',
    'D036_V101_%s_%s_STATS.csv',
    'D036_V101_%s_%s_TRADES.csv',
    'if(!g_fatal_pnl && g_in_trade)'
)){
    if(-not $check.Contains($needle)){throw "Generated v1.01 missing assertion: $needle"}
}
if($check.Contains('D036_V100_%s_%s_STATS.csv') -or $check.Contains('D036_V100_%s_%s_TRADES.csv')){
    throw 'Generated v1.01 still contains V100 output templates.'
}

$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash.ToLowerInvariant()
Write-Host "INSTALLE: $Target"
Write-Host "SHA256:   $hash"
Write-Host 'NEXT: compile this NEW v1.01 file in MetaEditor; then rerun only EURUSD and GBPUSD with D036_DEV_2024_2025.'
