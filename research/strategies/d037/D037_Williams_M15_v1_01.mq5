#property strict
#property version "1.01"
#property description "D037 Williams-inspired previous-day range volatility breakout V0 - FundedNext research harness"

// D037 V0 frozen research harness.
// NO ORDERS. Simulates executable-side entries/exits from tester M15 bars.
// Preregistration:
// research/campaigns/D037_WILLIAMS_PREVDAY_RANGE_VOLATILITY_BREAKOUT_V0_PREREGISTRATION_2026_09_06.md
//
// Frozen strategy:
// - broker D1 previous range = High(D-1)-Low(D-1)
// - current broker-day open = Open(D)
// - long trigger = day_open + 0.50*prev_range
// - short trigger = day_open - 0.50*prev_range
// - first threshold touched wins; both touched in same M15 bar => ambiguous day, no trade
// - max one trade / broker day, no reversal
// - stop distance = 0.50*prev_range from executable entry
// - no TP, no trailing, no filters
// - exit at stop or final executable M15 close of broker day
//
// Implementation clarification frozen before D037 results:
// - if an unambiguous entry and its stop are both contained in the same M15 bar,
//   the stop is assumed to occur after entry (conservative).
// - all entry/stop/exit prices must be finite and >0 before any P/L fallback is allowed.

enum D037_RUN_STAGE
  {
   D037_SMOKE_MAR2025 = 0,
   D037_DEV_2024_2025 = 1,
   D037_CONFIRM_2026_H1 = 2
  };

input D037_RUN_STAGE InpRunStage=D037_DEV_2024_2025;
input bool InpWriteCSV=true;

string SOURCE_NAME="D037_Williams_M15_v1_01.mq5";
string SOURCE_VERSION="1.01";

int g_trades_fh=INVALID_HANDLE;
int g_stats_fh=INVALID_HANDLE;
datetime g_last_bar_open=0;
datetime g_last_processed_bar=0;

datetime g_day_start=0;
int g_day_key=0;
double g_day_open=0.0;
double g_prev_high=0.0;
double g_prev_low=0.0;
double g_prev_range=0.0;
double g_long_trigger=0.0;
double g_short_trigger=0.0;
bool g_day_traded=false;
bool g_day_ambiguous=false;

bool g_in_trade=false;
bool g_long=false;
datetime g_signal_time=0;
datetime g_entry_time=0;
double g_entry=0.0;
double g_stop=0.0;
double g_risk_money=0.0;

long g_bars_seen=0;
long g_bars_in_stage=0;
long g_days_initialized=0;
long g_days_traded=0;
long g_ambiguous_days=0;
long g_signals=0;
long g_trades_opened=0;
long g_trades_closed=0;
long g_stop_exits=0;
long g_eod_exits=0;
long g_test_end_exits=0;
long g_invalid_price=0;
long g_invalid_risk=0;
long g_risk_fallbacks=0;
long g_pnl_fallbacks=0;
long g_risk_calc_failures=0;
long g_pnl_calc_failures=0;
long g_csv_rows=0;
string g_fatal_status="";

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
   if(InpRunStage==D037_SMOKE_MAR2025) return "SMOKE_MAR2025";
   if(InpRunStage==D037_DEV_2024_2025) return "DEV_2024_2025";
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

int DateKey(datetime t)
{
   MqlDateTime d;
   TimeToStruct(t,d);
   return d.year*10000+d.mon*100+d.day;
}

bool InStage(datetime broker_day_start)
{
   int ymd=DateKey(broker_day_start);
   if(InpRunStage==D037_SMOKE_MAR2025) return (ymd>=20250303 && ymd<=20250331);
   if(InpRunStage==D037_DEV_2024_2025) return (ymd>=20240102 && ymd<=20251231);
   return (ymd>=20260102 && ymd<=20260630);
}

bool ValidPrice(double x)
{
   return (x>0.0 && MathIsValidNumber(x));
}

void SetFatal(string status,string message)
{
   if(g_fatal_status=="") g_fatal_status=status;
   PrintFormat("D037 V101 FATAL | %s | %s",status,message);
}

double Spr(const MqlRates &b)
{
   return (double)b.spread*_Point;
}

double ClosePx(bool long_side,const MqlRates &b)
{
   return long_side ? b.close : b.close+Spr(b);
}

double CommissionUSD1Lot(double exit_px)
{
   if(!ValidPrice(g_entry) || !ValidPrice(exit_px)) return -1.0;
   string c=AssetClass();
   if(c=="FOREX") return 10.0;

   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract<=0.0 || !MathIsValidNumber(contract)) return -1.0;

   double rate=(c=="METAL" ? 0.000016 : 0.0004);
   double v=contract*g_entry*rate + contract*exit_px*rate;
   return (v>=0.0 && MathIsValidNumber(v)) ? v : -1.0;
}

bool CalcMoney1Lot(double entry_px,double exit_px,bool long_side,double &pnl,bool for_risk)
{
   if(!ValidPrice(entry_px) || !ValidPrice(exit_px)) return false;

   ENUM_ORDER_TYPE ot=long_side?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   ResetLastError();
   if(OrderCalcProfit(ot,_Symbol,1.0,entry_px,exit_px,pnl) && MathIsValidNumber(pnl))
      return true;

   int primary_err=GetLastError();

   if((StringFind(_Symbol,"EURUSD")>=0 || StringFind(_Symbol,"GBPUSD")>=0) && AssetClass()=="FOREX")
   {
      double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
      if(contract>0.0 && MathIsValidNumber(contract))
      {
         double delta=long_side ? (exit_px-entry_px) : (entry_px-exit_px);
         pnl=contract*delta;
         if(MathIsValidNumber(pnl))
         {
            if(for_risk) g_risk_fallbacks++; else g_pnl_fallbacks++;
            PrintFormat("D037 V101 %s FALLBACK | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f | pnl=%.8f",
                        for_risk?"RISK":"PNL",_Symbol,primary_err,entry_px,exit_px,pnl);
            return true;
         }
      }
   }

   PrintFormat("D037 V101 %s CALC FAILED | symbol=%s | primary_err=%d | entry=%.10f | exit=%.10f",
               for_risk?"RISK":"PNL",_Symbol,primary_err,entry_px,exit_px);
   return false;
}

bool RiskMoney(double entry_px,double stop_px,bool long_side,double &risk_money)
{
   double x=0.0;
   if(!CalcMoney1Lot(entry_px,stop_px,long_side,x,true)) return false;
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
   g_risk_money=0.0;
}

void ResetDay()
{
   g_day_start=0;
   g_day_key=0;
   g_day_open=0.0;
   g_prev_high=0.0;
   g_prev_low=0.0;
   g_prev_range=0.0;
   g_long_trigger=0.0;
   g_short_trigger=0.0;
   g_day_traded=false;
   g_day_ambiguous=false;
}

bool ReadD1Pair(datetime t,MqlRates &cur,MqlRates &prev)
{
   int shift=iBarShift(_Symbol,PERIOD_D1,t,false);
   if(shift<0) return false;

   MqlRates a[],b[];
   ArraySetAsSeries(a,true);
   ArraySetAsSeries(b,true);
   if(CopyRates(_Symbol,PERIOD_D1,shift,1,a)!=1) return false;
   if(CopyRates(_Symbol,PERIOD_D1,shift+1,1,b)!=1) return false;
   cur=a[0];
   prev=b[0];
   return true;
}

bool BrokerDayStart(datetime t,datetime &day_start)
{
   MqlRates cur,prev;
   if(!ReadD1Pair(t,cur,prev)) return false;
   day_start=cur.time;
   return (day_start>0);
}

bool LoadDaySetup(datetime t)
{
   MqlRates cur,prev;
   if(!ReadD1Pair(t,cur,prev))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","cannot resolve current/previous broker D1 bars");
      return false;
   }

   double day_open=cur.open;
   double prev_high=prev.high;
   double prev_low=prev.low;
   double prev_range=prev_high-prev_low;
   double long_trigger=day_open+0.50*prev_range;
   double short_trigger=day_open-0.50*prev_range;

   if(cur.time<=0 || prev.time<=0 || prev.time>=cur.time ||
      !ValidPrice(day_open) || !ValidPrice(prev_high) || !ValidPrice(prev_low) ||
      !(prev_high>prev_low) || !MathIsValidNumber(prev_range) || prev_range<=0.0 ||
      !ValidPrice(long_trigger) || !ValidPrice(short_trigger))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid broker-day setup price/range");
      return false;
   }

   g_day_start=cur.time;
   g_day_key=DateKey(cur.time);
   g_day_open=day_open;
   g_prev_high=prev_high;
   g_prev_low=prev_low;
   g_prev_range=prev_range;
   g_long_trigger=long_trigger;
   g_short_trigger=short_trigger;
   g_day_traded=false;
   g_day_ambiguous=false;
   g_days_initialized++;
   return true;
}

bool EnsureDay(datetime t)
{
   datetime ds=0;
   if(!BrokerDayStart(t,ds))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","cannot resolve broker day start");
      return false;
   }
   if(g_day_start==ds) return true;
   if(g_in_trade)
   {
      SetFatal("FINAL_INVALID_LIFECYCLE","day changed while prior trade remained open");
      return false;
   }
   ResetDay();
   return LoadDaySetup(t);
}

void WriteTrade(datetime exit_time,double exit_px,string why)
{
   if(!g_in_trade) return;

   if(!ValidPrice(g_entry) || !ValidPrice(g_stop) || !ValidPrice(exit_px))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","entry/stop/exit price invalid before PnL calculation");
      ResetTrade();
      return;
   }
   if(!(g_risk_money>0.0) || !MathIsValidNumber(g_risk_money))
   {
      g_invalid_risk++;
      SetFatal("FINAL_INVALID_RISK","stored initial risk invalid at close");
      ResetTrade();
      return;
   }

   double pnl=0.0;
   if(!CalcMoney1Lot(g_entry,exit_px,g_long,pnl,false))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","exit PnL calculation failed");
      ResetTrade();
      return;
   }

   double commission_usd=CommissionUSD1Lot(exit_px);
   if(commission_usd<0.0 || !MathIsValidNumber(commission_usd))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","commission calculation invalid");
      ResetTrade();
      return;
   }

   double gross_r=pnl/g_risk_money;
   double commission_r=commission_usd/g_risk_money;
   double net_r=gross_r-commission_r;
   double net_r_stress=gross_r-1.5*commission_r;
   if(!MathIsValidNumber(gross_r) || !MathIsValidNumber(commission_r) ||
      !MathIsValidNumber(net_r) || !MathIsValidNumber(net_r_stress))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","non-finite R metric");
      ResetTrade();
      return;
   }

   if(g_trades_fh!=INVALID_HANDLE)
   {
      FileWrite(g_trades_fh,
         StageName(),_Symbol,AssetClass(),CommissionRule(),IntegerToString(g_day_key),
         TimeToString(g_day_start,TIME_DATE|TIME_MINUTES),
         DoubleToString(g_day_open,_Digits),DoubleToString(g_prev_high,_Digits),DoubleToString(g_prev_low,_Digits),
         DoubleToString(g_prev_range,_Digits),DoubleToString(g_long_trigger,_Digits),DoubleToString(g_short_trigger,_Digits),
         g_long?"LONG":"SHORT",
         TimeToString(g_signal_time,TIME_DATE|TIME_MINUTES),TimeToString(g_entry_time,TIME_DATE|TIME_MINUTES),
         TimeToString(exit_time,TIME_DATE|TIME_MINUTES),
         DoubleToString(g_entry,_Digits),DoubleToString(g_stop,_Digits),DoubleToString(exit_px,_Digits),
         DoubleToString(g_risk_money,8),DoubleToString(gross_r,8),DoubleToString(commission_usd,8),
         DoubleToString(commission_r,8),DoubleToString(net_r,8),DoubleToString(net_r_stress,8),why
      );
      FileFlush(g_trades_fh);
      g_csv_rows++;
   }

   g_trades_closed++;
   if(why=="STOP") g_stop_exits++;
   else if(why=="EOD") g_eod_exits++;
   else if(why=="TEST_END") g_test_end_exits++;
   ResetTrade();
}

void WriteStats(string status)
{
   if(g_stats_fh==INVALID_HANDLE) return;
   FileWrite(g_stats_fh,status,SOURCE_NAME,SOURCE_VERSION,StageName(),
      g_bars_seen,g_bars_in_stage,g_days_initialized,g_days_traded,g_ambiguous_days,g_signals,
      g_trades_opened,g_trades_closed,g_stop_exits,g_eod_exits,g_test_end_exits,
      g_invalid_price,g_invalid_risk,g_risk_fallbacks,g_pnl_fallbacks,g_risk_calc_failures,g_pnl_calc_failures,g_csv_rows,
      _Symbol,EnumToString(_Period),AssetClass(),CommissionRule(),g_fatal_status,
      g_trades_name,g_stats_name,g_common_path+g_trades_name,g_common_path+g_stats_name);
   FileFlush(g_stats_fh);
}

bool EvaluateStopBar(const MqlRates &b)
{
   if(!g_in_trade) return false;
   double spread=Spr(b);
   if(spread<0.0 || !MathIsValidNumber(spread))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid M15 spread during stop evaluation");
      return false;
   }

   if(g_long)
   {
      if(b.low<=g_stop)
      {
         double fill=MathMin(g_stop,b.open);
         WriteTrade(b.time,fill,"STOP");
         return true;
      }
   }
   else
   {
      double ask_open=b.open+spread;
      double ask_high=b.high+spread;
      if(ask_high>=g_stop)
      {
         double fill=MathMax(g_stop,ask_open);
         WriteTrade(b.time,fill,"STOP");
         return true;
      }
   }
   return false;
}

void OpenFromBar(const MqlRates &b,bool long_side,double entry_px)
{
   g_signals++;
   g_long=long_side;
   g_signal_time=b.time;
   g_entry_time=b.time;
   g_entry=entry_px;
   g_stop=g_long ? g_entry-0.50*g_prev_range : g_entry+0.50*g_prev_range;

   if(!ValidPrice(g_entry) || !ValidPrice(g_stop))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","entry or initial stop invalid");
      ResetTrade();
      return;
   }

   double rm=0.0;
   if(!RiskMoney(g_entry,g_stop,g_long,rm))
   {
      g_invalid_risk++;
      g_risk_calc_failures++;
      SetFatal("FINAL_INVALID_RISK","initial risk calculation failed");
      ResetTrade();
      return;
   }

   g_risk_money=rm;
   g_in_trade=true;
   g_day_traded=true;
   g_days_traded++;
   g_trades_opened++;

   EvaluateStopBar(b);
}

void EvaluateEntryBar(const MqlRates &b)
{
   if(g_in_trade || g_day_traded || g_day_ambiguous || !InStage(g_day_start)) return;

   double spread=Spr(b);
   if(spread<0.0 || !MathIsValidNumber(spread) ||
      !ValidPrice(b.open) || !ValidPrice(b.high) || !ValidPrice(b.low) || !ValidPrice(b.close))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid M15 OHLC/spread during entry evaluation");
      return;
   }

   double ask_open=b.open+spread;
   double ask_high=b.high+spread;
   bool long_hit=(ask_high>=g_long_trigger);
   bool short_hit=(b.low<=g_short_trigger);

   if(long_hit && short_hit)
   {
      g_day_ambiguous=true;
      g_ambiguous_days++;
      return;
   }
   if(!long_hit && !short_hit) return;

   if(long_hit)
   {
      double fill=MathMax(g_long_trigger,ask_open);
      OpenFromBar(b,true,fill);
   }
   else
   {
      double fill=MathMin(g_short_trigger,b.open);
      OpenFromBar(b,false,fill);
   }
}

void ProcessClosedBar(const MqlRates &b)
{
   if(g_fatal_status!="") return;
   if(!EnsureDay(b.time)) return;

   g_bars_seen++;
   if(InStage(g_day_start)) g_bars_in_stage++;
   if(!InStage(g_day_start)) return;

   if(g_in_trade) EvaluateStopBar(b);
   if(g_fatal_status!="") return;
   if(!g_in_trade) EvaluateEntryBar(b);
}

void EndBrokerDay(const MqlRates &last_bar)
{
   if(g_fatal_status!="") return;
   if(g_in_trade)
   {
      double px=ClosePx(g_long,last_bar);
      WriteTrade(last_bar.time,px,"EOD");
   }
   if(g_fatal_status=="") ResetDay();
}

int OnInit()
{
   if(_Period!=PERIOD_M15)
   {
      PrintFormat("D037 V101 FATAL wrong timeframe | got=%s | required=PERIOD_M15",EnumToString(_Period));
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!InpWriteCSV)
   {
      Print("D037 V101 FATAL InpWriteCSV must remain true.");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!IsAllowedSymbol())
   {
      PrintFormat("D037 V101 FATAL symbol outside frozen universe | %s",_Symbol);
      return INIT_PARAMETERS_INCORRECT;
   }
   string account_ccy=AccountInfoString(ACCOUNT_CURRENCY);
   if(account_ccy!="USD")
   {
      PrintFormat("D037 V101 FATAL account currency must be USD | got=%s",account_ccy);
      return INIT_PARAMETERS_INCORRECT;
   }

   string sym=CleanSymbol();
   string stage=StageName();
   g_stats_name=StringFormat("D037_V101_%s_%s_STATS.csv",stage,sym);
   g_trades_name=StringFormat("D037_V101_%s_%s_TRADES.csv",stage,sym);
   g_common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";

   g_stats_fh=FileOpen(g_stats_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_stats_fh==INVALID_HANDLE)
   {
      PrintFormat("D037 V101 FATAL cannot open STATS | err=%d | %s%s",GetLastError(),g_common_path,g_stats_name);
      return INIT_FAILED;
   }
   FileWrite(g_stats_fh,"status","source_name","source_version","run_stage","bars_seen","bars_in_stage",
      "days_initialized","days_traded","ambiguous_days","entry_signals","trades_opened","trades_closed",
      "stop_exits","eod_exits","test_end_exits","invalid_price","invalid_risk","risk_fallbacks","pnl_fallbacks",
      "risk_calc_failures","pnl_calc_failures","csv_trade_rows","symbol","timeframe","asset_class","commission_rule",
      "fatal_status","trades_name","stats_name","trades_csv_fullpath","stats_csv_fullpath");
   WriteStats("INIT");

   g_trades_fh=FileOpen(g_trades_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_trades_fh==INVALID_HANDLE)
   {
      WriteStats("FATAL_TRADES_OPEN");
      PrintFormat("D037 V101 FATAL cannot open TRADES | err=%d | %s%s",GetLastError(),g_common_path,g_trades_name);
      FileClose(g_stats_fh); g_stats_fh=INVALID_HANDLE;
      return INIT_FAILED;
   }
   FileWrite(g_trades_fh,"run_stage","symbol","asset_class","commission_rule","day_key","broker_day_start",
      "day_open","prev_high","prev_low","prev_range","long_trigger","short_trigger","side","signal_time","entry_time",
      "exit_time","entry","initial_stop","exit","risk_money_1lot_usd","gross_r","commission_usd_1lot","commission_r",
      "net_r","net_r_commission_x1_5","exit_reason");
   FileFlush(g_trades_fh);
   WriteStats("READY");

   PrintFormat("D037 V101 READY | source=%s | stage=%s | symbol=%s | M15 | class=%s | NO ORDERS",SOURCE_NAME,stage,_Symbol,AssetClass());
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(g_fatal_status!="") return;

   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,PERIOD_M15,0,4,r)<3) return;

   if(g_last_bar_open==0)
   {
      g_last_bar_open=r[0].time;
      return;
   }
   if(r[0].time==g_last_bar_open) return;
   g_last_bar_open=r[0].time;

   MqlRates b=r[1];
   ProcessClosedBar(b);
   g_last_processed_bar=b.time;
   if(g_fatal_status!="") return;

   datetime next_day=0;
   if(!BrokerDayStart(r[0].time,next_day))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","cannot resolve next broker day at boundary check");
      return;
   }
   if(g_day_start!=0 && next_day!=g_day_start)
      EndBrokerDay(b);

   if((g_bars_seen%500)==0) WriteStats("PROGRESS");
}

void OnDeinit(const int reason)
{
   if(g_fatal_status=="")
   {
      MqlRates r[];
      ArraySetAsSeries(r,true);
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
   }

   string final_status=(g_fatal_status=="" ? "FINAL" : g_fatal_status);
   WriteStats(final_status);
   if(g_trades_fh!=INVALID_HANDLE){FileFlush(g_trades_fh);FileClose(g_trades_fh);g_trades_fh=INVALID_HANDLE;}
   if(g_stats_fh!=INVALID_HANDLE){FileFlush(g_stats_fh);FileClose(g_stats_fh);g_stats_fh=INVALID_HANDLE;}
   PrintFormat("D037 V101 FINAL | status=%s | stage=%s | symbol=%s | opened=%I64d | closed=%I64d | rows=%I64d | ambiguous_days=%I64d | invalid_price=%I64d | invalid_risk=%I64d | risk_fallbacks=%I64d | pnl_fallbacks=%I64d | pnl_failures=%I64d",
      final_status,StageName(),_Symbol,g_trades_opened,g_trades_closed,g_csv_rows,g_ambiguous_days,g_invalid_price,g_invalid_risk,g_risk_fallbacks,g_pnl_fallbacks,g_pnl_calc_failures);
}
