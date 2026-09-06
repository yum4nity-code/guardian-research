param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$RepoRoot='D:\MT5_Backtests\guardian-research'
$Source=Join-Path $RepoRoot 'research\strategies\d036\D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5'
$TargetDir='D:\MT5_FundedNext\MQL5\Experts\GuardianReasearch'
$Target=Join-Path $TargetDir 'D036_DonchianTrendBreakout_H1_v1_01_FUNDEDNEXT_PNLINTEGRITY_20260906.mq5'

if(-not(Test-Path -LiteralPath $Source)){throw "Source v1.00 introuvable: $Source"}
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

# Normalize source text once; all structural patches below use regexes and do not depend on CRLF/LF.
$raw=(Get-Content -LiteralPath $Source -Raw) -replace "`r`n","`n"

function Replace-RegexOne([string]$Text,[string]$Pattern,[string]$Replacement,[string]$Label){
    $rx=[regex]::new($Pattern,[System.Text.RegularExpressions.RegexOptions]::Singleline)
    $matches=$rx.Matches($Text)
    if($matches.Count -ne 1){throw "Patch anchor count for ${Label}: expected 1, got $($matches.Count)"}
    return $rx.Replace($Text,$Replacement,1)
}

# Unique source/version identity. v1.00 is never overwritten.
$raw=Replace-RegexOne $raw '#property\s+version\s+"1\.00"' '#property version "1.01"' 'property version'
$raw=Replace-RegexOne $raw 'D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906\.mq5' 'D036_DonchianTrendBreakout_H1_v1_01_FUNDEDNEXT_PNLINTEGRITY_20260906.mq5' 'source name'
$raw=Replace-RegexOne $raw 'string\s+SOURCE_VERSION\s*=\s*"1\.00"\s*;' 'string SOURCE_VERSION="1.01";' 'source version'

# Add explicit PnL-integrity counters directly after the known g_invalid_risk declaration.
$raw=Replace-RegexOne $raw 'long\s+g_invalid_risk\s*=\s*0\s*;\s*\n\s*long\s+g_csv_rows\s*=\s*0\s*;' @'
long g_invalid_risk=0;
long g_pnl_fallbacks=0;
long g_pnl_calc_failures=0;
long g_csv_rows=0;
bool g_fatal_pnl=false;
'@ 'global integrity counters'

# Primary OrderCalcProfit plus exact one-lot USD-quote fallback for EURUSD/GBPUSD only.
$moneyReplacement=@'
bool MoneyPnL(double exit_px,double &pnl)
{
   ENUM_ORDER_TYPE ot=g_long?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   ResetLastError();
   if(OrderCalcProfit(ot,_Symbol,1.0,g_entry,exit_px,pnl))
      return MathIsValidNumber(pnl);

   int primary_err=GetLastError();

   // Exact USD-quote fallback, frozen only for EURUSD/GBPUSD.
   // For one lot with USD quote currency: P/L = contract_size * signed price delta.
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
$raw=Replace-RegexOne $raw 'bool\s+MoneyPnL\s*\(double\s+exit_px\s*,\s*double\s*&pnl\s*\)\s*\{.*?\n\}' $moneyReplacement 'MoneyPnL function'

# Never silently discard an opened trade when PnL calculation fails.
$failReplacement=@'
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
$raw=Replace-RegexOne $raw 'double\s+pnl\s*=\s*0\.0\s*;\s*if\s*\(!MoneyPnL\(exit_px,pnl\)\s*\|\|\s*g_risk_money<=0\.0\)\s*\{.*?ResetTrade\(\);\s*return;\s*\}' $failReplacement 'WriteTrade failure handling'

# Extend STATS values and header with observability counters.
$raw=Replace-RegexOne $raw 'g_stop_exits\s*,\s*g_channel_exits\s*,\s*g_stage_end_exits\s*,\s*g_test_end_exits\s*,\s*g_invalid_risk\s*,\s*g_csv_rows\s*,' 'g_stop_exits,g_channel_exits,g_stage_end_exits,g_test_end_exits,g_invalid_risk,g_pnl_fallbacks,g_pnl_calc_failures,g_csv_rows,' 'WriteStats integrity values'
$raw=Replace-RegexOne $raw '"stop_exits"\s*,\s*"channel_exits"\s*,\s*"stage_end_exits"\s*,\s*"test_end_exits"\s*,\s*"invalid_risk"\s*,\s*"csv_trade_rows"\s*,\s*"symbol"' '"stop_exits","channel_exits","stage_end_exits","test_end_exits","invalid_risk","pnl_fallbacks","pnl_calc_failures","csv_trade_rows","symbol"' 'STATS integrity header'

# Stop further processing after an unrecoverable PnL failure.
$raw=Replace-RegexOne $raw 'void\s+OnTick\s*\(\s*\)\s*\{\s*\n\s*MqlRates\s+r\[\]\s*;' "void OnTick()`n{`n   if(g_fatal_pnl) return;`n   MqlRates r[];" 'OnTick fatal guard'

# Do not try to manufacture a valid FINAL after an unrecoverable PnL failure.
$raw=Replace-RegexOne $raw 'void\s+OnDeinit\s*\(const\s+int\s+reason\)\s*\{\s*\n\s*if\s*\(g_in_trade\)' "void OnDeinit(const int reason)`n{`n   if(!g_fatal_pnl && g_in_trade)" 'OnDeinit fatal guard'
$raw=Replace-RegexOne $raw 'WriteStats\s*\(\s*"FINAL"\s*\)\s*;' 'WriteStats(g_fatal_pnl ? "FINAL_INVALID_PNL_CALC" : "FINAL");' 'FINAL validity status'

# Deterministic v1.01 output names; v1.00 CSVs remain untouched.
$raw=Replace-RegexOne $raw 'D036_V100_%s_%s_STATS\.csv' 'D036_V101_%s_%s_STATS.csv' 'stats filename template'
$raw=Replace-RegexOne $raw 'D036_V100_%s_%s_TRADES\.csv' 'D036_V101_%s_%s_TRADES.csv' 'trades filename template'
$raw=$raw.Replace('D036 V100','D036 V101')

# Static integrity assertions BEFORE writing the file.
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
    if(-not $raw.Contains($needle)){throw "Generated v1.01 missing assertion: $needle"}
}
if($raw.Contains('D036_V100_%s_%s_STATS.csv') -or $raw.Contains('D036_V100_%s_%s_TRADES.csv')){
    throw 'Generated v1.01 still contains V100 output templates.'
}

Set-Content -LiteralPath $Target -Value $raw -Encoding UTF8
$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash.ToLowerInvariant()
Write-Host "INSTALLE: $Target"
Write-Host "SHA256:   $hash"
Write-Host 'OK: v1.01 generated with PnL-integrity fallback and fatal-run protection.'
Write-Host 'NEXT: compile this NEW v1.01 file in MetaEditor; then rerun only EURUSD and GBPUSD with D036_DEV_2024_2025.'
