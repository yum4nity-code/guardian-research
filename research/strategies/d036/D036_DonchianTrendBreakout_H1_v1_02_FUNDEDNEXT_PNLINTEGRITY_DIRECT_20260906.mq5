#property strict
#property version "1.02"
#property description "D036 Donchian/Turtle-inspired H1 trend breakout V0 - FundedNext research harness - PnL integrity"

// D036 V0 frozen research harness.
// NO ORDERS. Simulates executable-side entries/exits from tester H1 bars.
// Strategy semantics are preregistered in:
// research/campaigns/D036_DONCHIAN_TREND_BREAKOUT_H1_V0_PREREGISTRATION_2026_09_06.md
//
// Frozen V0:
// - signal close > prior 20-bar high => LONG; close < prior 20-bar low => SHORT
// - enter next H1 open on executable side
// - initial stop = 2.0 * ATR(20)
// - exit on initial stop or opposite prior 10-bar Donchian channel
// - no pyramiding, no TP, no time exit, no filters
// - one position max / symbol
// - conservative same-bar ambiguity handling
//
// v1.02 integrity-only patch:
// - strategy semantics unchanged versus v1.00
// - OrderCalcProfit remains primary PnL engine
// - exact 1-lot USD-quote fallback only for EURUSD/GBPUSD exit PnL
// - unrecoverable PnL failure invalidates the run instead of silently dropping a trade

enum D036_RUN_STAGE
  {
   D036_SMOKE_MAR2025 = 0,
   D036_DEV_2024_2025 = 1,
   D036_CONFIRM_2026_H1 = 2
  };

input D036_RUN_STAGE InpRunStage=D036_SMOKE_MAR2025;
input bool InpWriteCSV=true;

string SOURCE_NAME="D036_DonchianTrendBreakout_H1_v1_02_FUNDEDNEXT_PNLINTEGRITY_DIRECT_20260906.mq5";
string SOURCE_VERSION="1.02";

int g_atr_handle=INVALID_HANDLE;
int g_trades_fh=INVALID_HANDLE;
int g_stats_fh=INVALID_HANDLE;
datetime g_last_bar_open=0;

bool g_in_trade=false;
bool g_long=false;
datetime g_signal_time=0;
datetime g_entry_time=0;
double g_entry=0.0;
double g_stop=0.0;
double g_atr=0.0;
double g_entry_ch_hi=0.0;
double g_entry_ch_lo=0.0;
double g_risk_money=0.0;

long g_bars_seen=0;
long g_bars_in_stage=0;
long g_signals=0;
long g_trades_opened=0;
long g_trades_closed=0;
long g_stop_exits=0;
long g_channel_exits=0;
long g_stage_end_exits=0;
long g_test_end_exits=0;
long g_invalid_risk=0;
long g_pnl_fallbacks=0;
long g_pnl_calc_failures=0;
long g_csv_rows=0;
bool g_fatal_pnl=false;

string g_stats_name="";
string g_trades_name="";
string g_common_path="";

string CleanSymbol()
{
   string s=_Symbol;
   StringReplace(s,".","_");
   StringReplace(s,"#","_");
   StringReplace(s," ","_");
   return s;
}

string StageName()
{
   if(InpRunStage==D036_SMOKE_MAR2025) return "SMOKE_MAR2025";
   if(InpRunStage==D036_DEV_2024_2025) return "DEV_2024_2025";
   return "CONFIRM_2026_H1";
}

bool IsAllowedSymbol()
{
   return (StringFind(_Symbol,"BTCUSD")>=0 || StringFind(_Symbol,"ETHUSD")>=0 ||
           StringFind(_Symbol,"EURUSD")>=0 || StringFind(_Symbol,"GBPUSD")>=0 ||
           StringFind(_Symbol,"USDJPY")>=0 || StringFind(_Symbol,"XAUUSD")>=0);
}

string AssetClass()
{
   if(StringFind(_Symbol,"BTCUSD")>=0 || StringFind(_Symbol,"ETHUSD")>=0) return "CRYPTO";
   if(StringFind(_Symbol,"XAUUSD")>=0) return "METAL";
   return "FOREX";
}

string CommissionRule()
{
   string c=AssetClass();
   if(c=="FOREX") return "USD5_PER_LOT_PER_SIDE";
   if(c=="METAL") return "0.0016PCT_NOTIONAL_PER_SIDE";
   return "0.04PCT_NOTIONAL_PER_SIDE";
}

bool InStage(datetime t)
{
   MqlDateTime d;
   TimeToStruct(t,d);
   int ymd=d.year*10000+d.mon*100+d.day;
   if(InpRunStage==D036_SMOKE_MAR2025) return (ymd>=20250303 && ymd<=20250331);
   if(InpRunStage==D036_DEV_2024_2025) return (ymd>=20240102 && ymd<=20251231);
   return (ymd>=20260102 && ymd<=20260630);
}

double Spr(const MqlRates &b)
{
   return (double)b.spread*_Point;
}

double EntryPx(bool long_side,const MqlRates &b)
{
   return long_side ? b.open+Spr(b) : b.open;
}

double ClosePx(bool long_side,const MqlRates &b)
{
   return long_side ? b.close : b.close+Spr(b);
}

double HighestHigh(MqlRates &r[],int first_shift,int count)
{
   double x=-DBL_MAX;
   for(int i=first_shift;i<first_shift+count;i++) if(r[i].high>x) x=r[i].high;
   return x;
}

double LowestLow(MqlRates &r[],int first_shift,int count)
{
   double x=DBL_MAX;
   for(int i=first_shift;i<first_shift+count;i++) if(r[i].low<x) x=r[i].low;
   return x;
}

bool GetATR20(double &atr)
{
   double a[];
   ArraySetAsSeries(a,true);
   if(CopyBuffer(g_atr_handle,0,1,1,a)!=1) return false;
   atr=a[0];
   return (atr>0.0 && MathIsValidNumber(atr));
}

double CommissionUSD1Lot(double exit_px)
{
   string c=AssetClass();
   if(c=="FOREX") return 10.0; // USD 5 / lot / side, round trip

   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract<=0.0) return -1.0;

   double rate=(c=="METAL" ? 0.000016 : 0.0004); // 0.0016% or 0.04% per side
   return contract*g_entry*rate + contract*exit_px*rate;
}

bool MoneyPnL(double exit_px,double &pnl)
{
   ENUM_ORDER_TYPE ot=g_long?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   ResetLastError();
   if(OrderCalcProfit(ot,_Symbol,1.0,g_entry,exit_px,pnl))
      return MathIsValidNumber(pnl);

   int primary_err=GetLastError();

   // Exact one-lot fallback for USD-quoted FX only.
   // EURUSD/GBPUSD P/L in USD = contract_size * signed price delta.
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
            PrintFormat("D036 V102 PNL FALLBACK | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f | pnl=%.8f",_Symbol,primary_err,g_entry,exit_px,pnl);
            return true;
         }
      }
   }

   PrintFormat("D036 V102 FATAL MoneyPnL failed | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f",_Symbol,primary_err,g_entry,exit_px);
   return false;
}

bool RiskMoney(double &risk_money)
{
   ENUM_ORDER_TYPE ot=g_long?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double x=0.0;
   if(!OrderCalcProfit(ot,_Symbol,1.0,g_entry,g_stop,x)) return false;
   risk_money=MathAbs(x);
   return (risk_money>0.0 && MathIsValidNumber(risk_money));
}

void ResetTrade()
{
   g_in_trade=false;
   g_long=false;
   g_signal_time=0;
   g_entry_time=0;
   g_entry=0.0;
   g_stop=0.0;
   g_atr=0.0;
   g_entry_ch_hi=0.0;
   g_entry_ch_lo=0.0;
   g_risk_money=0.0;
}

void WriteTrade(datetime exit_time,double exit_px,double exit_channel,string why)
{
   if(!g_in_trade) return;

   double pnl=0.0;
   if(!MoneyPnL(exit_px,pnl) || g_risk_money<=0.0)
   {
      g_pnl_calc_failures++;
      g_fatal_pnl=true;
      PrintFormat("D036 V102 FATAL trade PnL calc failed | symbol=%s | exit=%s",_Symbol,TimeToString(exit_time,TIME_DATE|TIME_MINUTES));
      ResetTrade();
      return;
   }

   double gross_r=pnl/g_risk_money;
   double commission_usd=CommissionUSD1Lot(exit_px);
   double commission_r=(commission_usd>=0.0 ? commission_usd/g_risk_money : 0.0);
   double net_r=gross_r-commission_r;
   double net_r_stress=gross_r-1.5*commission_r;

   if(g_trades_fh!=INVALID_HANDLE)
   {
      FileWrite(g_trades_fh,
         StageName(),_Symbol,AssetClass(),CommissionRule(),
         g_long?"LONG":"SHORT",
         TimeToString(g_signal_time,TIME_DATE|TIME_MINUTES),
         TimeToString(g_entry_time,TIME_DATE|TIME_MINUTES),
         TimeToString(exit_time,TIME_DATE|TIME_MINUTES),
         DoubleToString(g_entry_ch_hi,_Digits),DoubleToString(g_entry_ch_lo,_Digits),
         DoubleToString(exit_channel,_Digits),DoubleToString(g_atr,_Digits),
         DoubleToString(g_entry,_Digits),DoubleToString(g_stop,_Digits),DoubleToString(exit_px,_Digits),
         DoubleToString(g_risk_money,8),DoubleToString(gross_r,8),
         DoubleToString(commission_usd,8),DoubleToString(commission_r,8),
         DoubleToString(net_r,8),DoubleToString(net_r_stress,8),why
      );
      FileFlush(g_trades_fh);
      g_csv_rows++;
   }

   g_trades_closed++;
   if(why=="STOP") g_stop_exits++;
   else if(why=="CHANNEL10") g_channel_exits++;
   else if(why=="STAGE_END") g_stage_end_exits++;
   else if(why=="TEST_END") g_test_end_exits++;
   ResetTrade();
}

void WriteStats(string status)
{
   if(g_stats_fh==INVALID_HANDLE) return;
   FileWrite(g_stats_fh,status,SOURCE_NAME,SOURCE_VERSION,StageName(),
      g_bars_seen,g_bars_in_stage,g_signals,g_trades_opened,g_trades_closed,
      g_stop_exits,g_channel_exits,g_stage_end_exits,g_test_end_exits,g_invalid_risk,g_pnl_fallbacks,g_pnl_calc_failures,g_csv_rows,
      _Symbol,EnumToString(_Period),AssetClass(),CommissionRule(),
      g_trades_name,g_stats_name,g_common_path+g_trades_name,g_common_path+g_stats_name);
   FileFlush(g_stats_fh);
}

bool EvaluateExit(MqlRates &r[])
{
   if(!g_in_trade) return false;
   MqlRates b=r[1];
   double ch_hi=HighestHigh(r,2,10);
   double ch_lo=LowestLow(r,2,10);
   double spread=Spr(b);

   bool stop_hit=false,channel_hit=false;
   double stop_fill=0.0,channel_fill=0.0,chosen=0.0,exit_channel=0.0;

   if(g_long)
   {
      stop_hit=(b.low<=g_stop);
      channel_hit=(b.low<=ch_lo);
      stop_fill=MathMin(g_stop,b.open);
      channel_fill=MathMin(ch_lo,b.open);
      exit_channel=ch_lo;
      if(stop_hit && channel_hit)
      {
         chosen=MathMin(stop_fill,channel_fill); // conservative same-bar ambiguity
         WriteTrade(b.time,chosen,exit_channel,(chosen==stop_fill?"STOP":"CHANNEL10"));
         return true;
      }
      if(stop_hit){WriteTrade(b.time,stop_fill,exit_channel,"STOP");return true;}
      if(channel_hit){WriteTrade(b.time,channel_fill,exit_channel,"CHANNEL10");return true;}
   }
   else
   {
      double ask_open=b.open+spread;
      stop_hit=(b.high+spread>=g_stop);
      channel_hit=(b.high>=ch_hi);
      stop_fill=MathMax(g_stop,ask_open);
      channel_fill=MathMax(ch_hi+spread,ask_open);
      exit_channel=ch_hi;
      if(stop_hit && channel_hit)
      {
         chosen=MathMax(stop_fill,channel_fill); // conservative same-bar ambiguity
         WriteTrade(b.time,chosen,exit_channel,(chosen==stop_fill?"STOP":"CHANNEL10"));
         return true;
      }
      if(stop_hit){WriteTrade(b.time,stop_fill,exit_channel,"STOP");return true;}
      if(channel_hit){WriteTrade(b.time,channel_fill,exit_channel,"CHANNEL10");return true;}
   }
   return false;
}

void EvaluateEntry(MqlRates &r[])
{
   if(g_in_trade) return;
   if(!InStage(r[1].time) || !InStage(r[0].time)) return;

   double hi20=HighestHigh(r,2,20);
   double lo20=LowestLow(r,2,20);
   bool long_sig=(r[1].close>hi20);
   bool short_sig=(r[1].close<lo20);
   if(long_sig==short_sig) return;

   double atr=0.0;
   if(!GetATR20(atr)) return;

   g_signals++;
   g_long=long_sig;
   g_signal_time=r[1].time;
   g_entry_time=r[0].time;
   g_entry=EntryPx(g_long,r[0]);
   g_atr=atr;
   g_entry_ch_hi=hi20;
   g_entry_ch_lo=lo20;
   g_stop=g_long ? g_entry-2.0*atr : g_entry+2.0*atr;

   double rm=0.0;
   if(g_entry<=0.0 || g_stop<=0.0 || !RiskMoney(rm))
   {
      g_invalid_risk++;
      ResetTrade();
      return;
   }
   g_risk_money=rm;
   g_in_trade=true;
   g_trades_opened++;
}

int OnInit()
{
   if(_Period!=PERIOD_H1)
   {
      PrintFormat("D036 V102 FATAL wrong timeframe | got=%s | required=PERIOD_H1",EnumToString(_Period));
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!InpWriteCSV)
   {
      Print("D036 V102 FATAL InpWriteCSV must remain true.");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!IsAllowedSymbol())
   {
      PrintFormat("D036 V102 FATAL symbol outside frozen universe | %s",_Symbol);
      return INIT_PARAMETERS_INCORRECT;
   }
   string account_ccy=AccountInfoString(ACCOUNT_CURRENCY);
   if(account_ccy!="USD")
   {
      PrintFormat("D036 V102 FATAL account currency must be USD for frozen commission model | got=%s",account_ccy);
      return INIT_PARAMETERS_INCORRECT;
   }

   g_atr_handle=iATR(_Symbol,PERIOD_H1,20);
   if(g_atr_handle==INVALID_HANDLE)
   {
      PrintFormat("D036 V102 FATAL iATR handle failed | err=%d",GetLastError());
      return INIT_FAILED;
   }

   string sym=CleanSymbol();
   string stage=StageName();
   g_stats_name=StringFormat("D036_V102_%s_%s_STATS.csv",stage,sym);
   g_trades_name=StringFormat("D036_V102_%s_%s_TRADES.csv",stage,sym);
   g_common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";

   g_stats_fh=FileOpen(g_stats_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_stats_fh==INVALID_HANDLE)
   {
      PrintFormat("D036 V102 FATAL cannot open STATS | err=%d | %s%s",GetLastError(),g_common_path,g_stats_name);
      return INIT_FAILED;
   }
   FileWrite(g_stats_fh,"status","source_name","source_version","run_stage","bars_seen","bars_in_stage","breakout_signals","trades_opened","trades_closed","stop_exits","channel_exits","stage_end_exits","test_end_exits","invalid_risk","pnl_fallbacks","pnl_calc_failures","csv_trade_rows","symbol","timeframe","asset_class","commission_rule","trades_name","stats_name","trades_csv_fullpath","stats_csv_fullpath");
   WriteStats("INIT");

   g_trades_fh=FileOpen(g_trades_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_trades_fh==INVALID_HANDLE)
   {
      WriteStats("FATAL_TRADES_OPEN");
      PrintFormat("D036 V102 FATAL cannot open TRADES | err=%d | %s%s",GetLastError(),g_common_path,g_trades_name);
      FileClose(g_stats_fh); g_stats_fh=INVALID_HANDLE;
      return INIT_FAILED;
   }
   FileWrite(g_trades_fh,"run_stage","symbol","asset_class","commission_rule","side","signal_time","entry_time","exit_time","entry_channel_hi20","entry_channel_lo20","exit_channel10","atr20","entry","initial_stop","exit","risk_money_1lot_usd","gross_r","commission_usd_1lot","commission_r","net_r","net_r_commission_x1_5","exit_reason");
   FileFlush(g_trades_fh);
   WriteStats("READY");

   PrintFormat("D036 V102 READY | source=%s | stage=%s | symbol=%s | H1 | class=%s | NO ORDERS",SOURCE_NAME,stage,_Symbol,AssetClass());
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(g_fatal_pnl) return;

   MqlRates r[];
   ArraySetAsSeries(r,true);
   int n=CopyRates(_Symbol,PERIOD_H1,0,40,r);
   if(n<25) return;

   if(g_last_bar_open==0)
   {
      g_last_bar_open=r[0].time;
      return;
   }
   if(r[0].time==g_last_bar_open) return;
   g_last_bar_open=r[0].time;
   g_bars_seen++;
   if(InStage(r[1].time)) g_bars_in_stage++;

   if(g_in_trade && InStage(r[1].time)) EvaluateExit(r);

   // Do not carry development/smoke trades into a locked period.
   if(g_in_trade && InStage(r[1].time) && !InStage(r[0].time))
   {
      WriteTrade(r[1].time,ClosePx(g_long,r[1]),0.0,"STAGE_END");
      WriteStats("PROGRESS");
      return;
   }

   EvaluateEntry(r);

   if((g_bars_seen%250)==0) WriteStats("PROGRESS");
}

void OnDeinit(const int reason)
{
   if(!g_fatal_pnl && g_in_trade)
   {
      MqlRates r[];
      ArraySetAsSeries(r,true);
      if(CopyRates(_Symbol,PERIOD_H1,0,3,r)>=2 && InStage(r[1].time))
         WriteTrade(r[1].time,ClosePx(g_long,r[1]),0.0,"TEST_END");
      else
         ResetTrade();
   }

   WriteStats(g_fatal_pnl ? "FINAL_INVALID_PNL_CALC" : "FINAL");
   if(g_trades_fh!=INVALID_HANDLE){FileFlush(g_trades_fh);FileClose(g_trades_fh);g_trades_fh=INVALID_HANDLE;}
   if(g_stats_fh!=INVALID_HANDLE){FileFlush(g_stats_fh);FileClose(g_stats_fh);g_stats_fh=INVALID_HANDLE;}
   if(g_atr_handle!=INVALID_HANDLE){IndicatorRelease(g_atr_handle);g_atr_handle=INVALID_HANDLE;}
   PrintFormat("D036 V102 FINAL | stage=%s | symbol=%s | trades=%d | rows=%d | stops=%d | channels=%d | fallbacks=%d | pnl_failures=%d",StageName(),_Symbol,g_trades_closed,g_csv_rows,g_stop_exits,g_channel_exits,g_pnl_fallbacks,g_pnl_calc_failures);
}
