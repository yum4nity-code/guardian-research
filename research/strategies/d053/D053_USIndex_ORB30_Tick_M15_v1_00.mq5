#property strict
#property version "1.01"
#property description "D053 FundedNext US Index ORB30 entry-alpha benchmark V0 - tick execution - session-close lifecycle amendment"

input bool InpWriteCSV=true;

string EXPERIMENT_ID="D053-US-INDEX-ORB30-ENTRY-ALPHA-V0";
string SOURCE_NAME="D053_USIndex_ORB30_Tick_M15_v1_00.mq5";
string SOURCE_VERSION="1.01";
string RUN_TOKEN="RUN";

const int OR_START_MINUTE=16*60+30;
const int OR_END_MINUTE=17*60;
const int EOD_EXIT_MINUTE=22*60+45;

int g_stats_fh=INVALID_HANDLE;
int g_trades_fh=INVALID_HANDLE;
string g_stats_name="";
string g_trades_name="";
string g_common_path="";

int g_day_key=0;
bool g_range_finalized=false;
bool g_range_usable=false;
bool g_day_traded=false;
bool g_day_ambiguous=false;
long g_or_ticks=0;
double g_or_ask_high=0.0;
double g_or_bid_low=0.0;

bool g_in_trade=false;
bool g_long=false;
datetime g_entry_time=0;
long g_entry_msc=0;
double g_entry=0.0;
double g_stop=0.0;
double g_entry_spread=0.0;
double g_risk_money=0.0;
string g_trade_id="";

bool g_have_last_tick=false;
MqlTick g_last_tick;

double g_mfe_r=0.0;
double g_mae_r=0.0;
datetime g_mfe_time=0;
datetime g_mae_time=0;
long g_mfe_msc=0;
long g_mae_msc=0;
double g_max_retrace_from_mfe=0.0;

long g_ticks_seen=0;
long g_days_seen=0;
long g_range_days=0;
long g_range_unusable_days=0;
long g_ambiguous_days=0;
long g_entry_signals=0;
long g_trades_opened=0;
long g_trades_closed=0;
long g_stop_exits=0;
long g_eod_exits=0;
long g_test_end_exits=0;
long g_day_change_open_trade=0;
long g_invalid_price=0;
long g_invalid_risk=0;
long g_risk_calc_failures=0;
long g_pnl_calc_failures=0;
long g_path_calc_failures=0;
long g_csv_rows=0;
string g_fatal_status="";

string CleanSymbol()
{
   string s=_Symbol;
   StringReplace(s,".","_");
   StringReplace(s,"#","_");
   StringReplace(s," ","_");
   return s;
}

bool IsAllowedSymbol()
{
   return (StringFind(_Symbol,"SPX500")>=0 ||
           StringFind(_Symbol,"NDX100")>=0 ||
           StringFind(_Symbol,"US30")>=0 ||
           StringFind(_Symbol,"US2000")>=0);
}

bool ValidPrice(double x){ return (x>0.0 && MathIsValidNumber(x)); }
long TickMsc(const MqlTick &tick){ return (tick.time_msc>0 ? tick.time_msc : ((long)tick.time)*1000); }

int DateKey(datetime t)
{
   MqlDateTime d;
   TimeToStruct(t,d);
   return d.year*10000+d.mon*100+d.day;
}

int MinuteOfDay(datetime t)
{
   MqlDateTime d;
   TimeToStruct(t,d);
   return d.hour*60+d.min;
}

string TimeSecond(datetime t)
{
   return (t>0 ? TimeToString(t,TIME_DATE|TIME_SECONDS) : "");
}

void SetFatal(string status,string message)
{
   if(g_fatal_status=="") g_fatal_status=status;
   PrintFormat("D053 V101 FATAL | %s | %s",status,message);
}

bool CalcMoney1Lot(double entry_px,double exit_px,bool long_side,double &pnl)
{
   if(!ValidPrice(entry_px) || !ValidPrice(exit_px)) return false;
   ENUM_ORDER_TYPE order_type=long_side ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   ResetLastError();
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry_px,exit_px,pnl)) return false;
   return MathIsValidNumber(pnl);
}

bool RiskMoney(double entry_px,double stop_px,bool long_side,double &risk_money)
{
   double pnl=0.0;
   if(!CalcMoney1Lot(entry_px,stop_px,long_side,pnl)) return false;
   risk_money=MathAbs(pnl);
   return (risk_money>0.0 && MathIsValidNumber(risk_money));
}

bool PnlMoney(double entry_px,double exit_px,bool long_side,double &pnl)
{
   return CalcMoney1Lot(entry_px,exit_px,long_side,pnl);
}

bool PathR(double liquidation_px,double &r)
{
   if(!(g_risk_money>0.0) || !MathIsValidNumber(g_risk_money)) return false;
   double pnl=0.0;
   if(!PnlMoney(g_entry,liquidation_px,g_long,pnl)) return false;
   r=pnl/g_risk_money;
   return MathIsValidNumber(r);
}

double ExtraSpreadStressMoney(double exit_spread)
{
   if(!ValidPrice(g_entry) || g_entry_spread<0.0 || exit_spread<0.0) return -1.0;
   double extra_price=0.25*(g_entry_spread+exit_spread);
   if(extra_price<0.0 || !MathIsValidNumber(extra_price)) return -1.0;
   if(extra_price==0.0) return 0.0;

   double stressed_exit=g_long ? (g_entry-extra_price) : (g_entry+extra_price);
   if(!ValidPrice(stressed_exit)) return -1.0;
   double pnl=0.0;
   if(!PnlMoney(g_entry,stressed_exit,g_long,pnl)) return -1.0;
   double money=MathAbs(pnl);
   return (money>=0.0 && MathIsValidNumber(money)) ? money : -1.0;
}

void ResetPath()
{
   g_mfe_r=0.0;
   g_mae_r=0.0;
   g_mfe_time=0;
   g_mae_time=0;
   g_mfe_msc=0;
   g_mae_msc=0;
   g_max_retrace_from_mfe=0.0;
}

void ResetTrade()
{
   g_in_trade=false;
   g_long=false;
   g_entry_time=0;
   g_entry_msc=0;
   g_entry=0.0;
   g_stop=0.0;
   g_entry_spread=0.0;
   g_risk_money=0.0;
   g_trade_id="";
   ResetPath();
}

void ResetDay(int day_key)
{
   g_day_key=day_key;
   g_range_finalized=false;
   g_range_usable=false;
   g_day_traded=false;
   g_day_ambiguous=false;
   g_or_ticks=0;
   g_or_ask_high=0.0;
   g_or_bid_low=0.0;
   g_days_seen++;
}

void ObservePath(const MqlTick &tick)
{
   if(!g_in_trade || g_fatal_status!="") return;
   double liquidation=g_long ? tick.bid : tick.ask;
   if(!ValidPrice(liquidation))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid executable liquidation during path");
      return;
   }
   double current_r=0.0;
   if(!PathR(liquidation,current_r))
   {
      g_path_calc_failures++;
      SetFatal("FINAL_INVALID_PATH_CALC","cannot calculate path R");
      return;
   }

   long msc=TickMsc(tick);
   if(current_r>g_mfe_r)
   {
      g_mfe_r=current_r;
      g_mfe_time=tick.time;
      g_mfe_msc=msc;
   }
   double adverse=-current_r;
   if(adverse>g_mae_r)
   {
      g_mae_r=adverse;
      g_mae_time=tick.time;
      g_mae_msc=msc;
   }
   double retrace=g_mfe_r-current_r;
   if(retrace>g_max_retrace_from_mfe) g_max_retrace_from_mfe=retrace;
}

void WriteStats(string status)
{
   if(g_stats_fh==INVALID_HANDLE) return;
   FileWrite(g_stats_fh,
      status,SOURCE_NAME,SOURCE_VERSION,RUN_TOKEN,
      g_ticks_seen,g_days_seen,g_range_days,g_range_unusable_days,g_ambiguous_days,
      g_entry_signals,g_trades_opened,g_trades_closed,g_stop_exits,g_eod_exits,g_test_end_exits,
      g_day_change_open_trade,g_invalid_price,g_invalid_risk,g_risk_calc_failures,
      g_pnl_calc_failures,g_path_calc_failures,g_csv_rows,_Symbol,EnumToString(_Period),
      "INDEX","EXECUTABLE_SPREAD_PLUS_1_5X_SPREAD_STRESS",g_fatal_status,
      g_trades_name,g_stats_name,g_common_path+g_trades_name,g_common_path+g_stats_name);
   FileFlush(g_stats_fh);
}

void CloseTrade(const MqlTick &tick,string why)
{
   if(!g_in_trade) return;
   double exit_px=g_long ? tick.bid : tick.ask;
   double exit_spread=tick.ask-tick.bid;

   if(!ValidPrice(exit_px) || exit_spread<0.0 || !MathIsValidNumber(exit_spread))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid exit price/spread");
      ResetTrade();
      return;
   }

   double pnl=0.0;
   if(!PnlMoney(g_entry,exit_px,g_long,pnl))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","cannot calculate trade pnl");
      ResetTrade();
      return;
   }

   double extra_stress_money=ExtraSpreadStressMoney(exit_spread);
   if(extra_stress_money<0.0 || !MathIsValidNumber(extra_stress_money))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","cannot calculate spread stress");
      ResetTrade();
      return;
   }

   double gross_r=pnl/g_risk_money;
   double net_r=gross_r;
   double stress_r=net_r-extra_stress_money/g_risk_money;
   if(!MathIsValidNumber(gross_r) || !MathIsValidNumber(net_r) || !MathIsValidNumber(stress_r))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","non-finite R metric");
      ResetTrade();
      return;
   }

   double time_to_mfe=(g_mfe_msc>0 ? ((double)(g_mfe_msc-g_entry_msc))/60000.0 : 0.0);
   double time_to_mae=(g_mae_msc>0 ? ((double)(g_mae_msc-g_entry_msc))/60000.0 : 0.0);

   if(g_trades_fh!=INVALID_HANDLE)
   {
      FileWrite(g_trades_fh,
         RUN_TOKEN,_Symbol,IntegerToString(g_day_key),
         DoubleToString(g_or_ask_high,_Digits),DoubleToString(g_or_bid_low,_Digits),
         g_long?"LONG":"SHORT",TimeSecond(g_entry_time),TimeSecond(tick.time),
         DoubleToString(g_entry,_Digits),DoubleToString(g_stop,_Digits),DoubleToString(exit_px,_Digits),
         DoubleToString(g_entry_spread,_Digits),DoubleToString(exit_spread,_Digits),
         DoubleToString(g_risk_money,8),DoubleToString(gross_r,8),DoubleToString(net_r,8),
         DoubleToString(stress_r,8),why,g_trade_id,
         DoubleToString(g_mfe_r,8),DoubleToString(g_mae_r,8),
         TimeSecond(g_mfe_time),TimeSecond(g_mae_time),
         (g_mfe_msc>0?DoubleToString(time_to_mfe,6):""),
         (g_mae_msc>0?DoubleToString(time_to_mae,6):""),
         DoubleToString(g_max_retrace_from_mfe,8));
      FileFlush(g_trades_fh);
      g_csv_rows++;
   }

   g_trades_closed++;
   if(why=="STOP") g_stop_exits++;
   else if(why=="EOD" || why=="SESSION_END") g_eod_exits++;
   else if(why=="TEST_END") g_test_end_exits++;
   ResetTrade();
}

void FinalizeOpeningRange()
{
   if(g_range_finalized) return;
   g_range_finalized=true;
   if(g_or_ticks<=0 || !ValidPrice(g_or_ask_high) || !ValidPrice(g_or_bid_low) || g_or_ask_high<=g_or_bid_low)
   {
      g_range_usable=false;
      g_range_unusable_days++;
      return;
   }
   g_range_usable=true;
   g_range_days++;
}

void OpenTrade(const MqlTick &tick,bool long_side)
{
   g_entry_signals++;
   g_long=long_side;
   g_entry_time=tick.time;
   g_entry_msc=TickMsc(tick);
   g_entry=g_long ? tick.ask : tick.bid;
   g_stop=g_long ? g_or_bid_low : g_or_ask_high;
   g_entry_spread=tick.ask-tick.bid;

   if(!ValidPrice(g_entry) || !ValidPrice(g_stop) || g_entry_spread<0.0 || !MathIsValidNumber(g_entry_spread))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid entry/stop/spread");
      ResetTrade();
      return;
   }
   if((g_long && g_stop>=g_entry) || (!g_long && g_stop<=g_entry))
   {
      g_invalid_risk++;
      SetFatal("FINAL_INVALID_RISK","stop is not adverse to entry");
      ResetTrade();
      return;
   }

   double risk=0.0;
   if(!RiskMoney(g_entry,g_stop,g_long,risk))
   {
      g_invalid_risk++;
      g_risk_calc_failures++;
      SetFatal("FINAL_INVALID_RISK","initial risk calculation failed");
      ResetTrade();
      return;
   }

   g_risk_money=risk;
   g_trade_id=StringFormat("%s_%d_%s",CleanSymbol(),g_day_key,g_long?"LONG":"SHORT");
   g_in_trade=true;
   g_day_traded=true;
   g_trades_opened++;
   ResetPath();
   ObservePath(tick);
}

void EvaluateEntry(const MqlTick &tick)
{
   if(g_in_trade || g_day_traded || g_day_ambiguous || !g_range_usable || g_fatal_status!="") return;
   int minute=MinuteOfDay(tick.time);
   if(minute<OR_END_MINUTE || minute>=EOD_EXIT_MINUTE) return;

   double trade_tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!(trade_tick>0.0) || !MathIsValidNumber(trade_tick))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","SYMBOL_TRADE_TICK_SIZE unavailable");
      return;
   }

   double long_trigger=g_or_ask_high+trade_tick;
   double short_trigger=g_or_bid_low-trade_tick;
   bool long_hit=(tick.ask>=long_trigger);
   bool short_hit=(tick.bid<=short_trigger);

   if(long_hit && short_hit)
   {
      g_day_ambiguous=true;
      g_ambiguous_days++;
      PrintFormat("D053 V101 AMBIGUOUS SAME TICK | symbol=%s | day=%d",_Symbol,g_day_key);
      return;
   }
   if(long_hit) OpenTrade(tick,true);
   else if(short_hit) OpenTrade(tick,false);
}

void EvaluateStop(const MqlTick &tick)
{
   if(!g_in_trade || g_fatal_status!="") return;
   if(g_long)
   {
      if(tick.bid<=g_stop) CloseTrade(tick,"STOP");
   }
   else
   {
      if(tick.ask>=g_stop) CloseTrade(tick,"STOP");
   }
}

int OnInit()
{
   if(_Period!=PERIOD_M15)
   {
      PrintFormat("D053 V101 FATAL wrong timeframe | got=%s | required=M15",EnumToString(_Period));
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!InpWriteCSV)
   {
      Print("D053 V101 FATAL InpWriteCSV must remain true");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!IsAllowedSymbol())
   {
      PrintFormat("D053 V101 FATAL symbol outside frozen universe | %s",_Symbol);
      return INIT_PARAMETERS_INCORRECT;
   }
   if(AccountInfoString(ACCOUNT_CURRENCY)!="USD")
   {
      PrintFormat("D053 V101 FATAL account currency must be USD | got=%s",AccountInfoString(ACCOUNT_CURRENCY));
      return INIT_PARAMETERS_INCORRECT;
   }

   string sym=CleanSymbol();
   g_stats_name=StringFormat("D053_V100_RUN_%s_STATS.csv",sym);
   g_trades_name=StringFormat("D053_V100_RUN_%s_TRADES.csv",sym);
   g_common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";

   g_stats_fh=FileOpen(g_stats_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_stats_fh==INVALID_HANDLE)
   {
      PrintFormat("D053 V101 FATAL cannot open stats | err=%d",GetLastError());
      return INIT_FAILED;
   }

   FileWrite(g_stats_fh,
      "status","source_name","source_version","run_stage",
      "ticks_seen","days_seen","range_days","range_unusable_days","ambiguous_days",
      "entry_signals","trades_opened","trades_closed","stop_exits","eod_exits","test_end_exits",
      "day_change_open_trade","invalid_price","invalid_risk","risk_calc_failures",
      "pnl_calc_failures","path_calc_failures","csv_trade_rows","symbol","timeframe",
      "asset_class","cost_rule","fatal_status","trades_name","stats_name",
      "trades_csv_fullpath","stats_csv_fullpath");
   WriteStats("INIT");

   g_trades_fh=FileOpen(g_trades_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_trades_fh==INVALID_HANDLE)
   {
      PrintFormat("D053 V101 FATAL cannot open trades | err=%d",GetLastError());
      WriteStats("FATAL_TRADES_OPEN");
      FileClose(g_stats_fh);
      g_stats_fh=INVALID_HANDLE;
      return INIT_FAILED;
   }

   FileWrite(g_trades_fh,
      "run_stage","symbol","day_key","or_ask_high","or_bid_low","side",
      "entry_time","exit_time","entry","initial_stop","exit",
      "entry_spread","exit_spread","risk_money_1lot_usd",
      "gross_r","net_r","net_r_spread_x1_5","exit_reason","trade_id",
      "mfe_r","mae_r","mfe_time","mae_time","time_to_mfe_minutes",
      "time_to_mae_minutes","max_retracement_from_mfe_r");
   FileFlush(g_trades_fh);

   ResetTrade();
   g_day_key=0;
   WriteStats("READY");
   PrintFormat("D053 V101 READY | source=%s | symbol=%s | OR=16:30-17:00 server | nominal exit=22:45 | SESSION_END fallback | NO ORDERS",SOURCE_NAME,_Symbol);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(g_fatal_status!="") return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   if(tick.time<=0 || !ValidPrice(tick.bid) || !ValidPrice(tick.ask) || tick.ask<tick.bid)
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid tick");
      return;
   }
   g_ticks_seen++;

   int day=DateKey(tick.time);
   if(g_day_key==0)
   {
      ResetDay(day);
   }
   else if(day!=g_day_key)
   {
      if(g_in_trade)
      {
         if(!g_have_last_tick || DateKey(g_last_tick.time)!=g_day_key)
         {
            g_day_change_open_trade++;
            SetFatal("FINAL_INVALID_LIFECYCLE","broker day changed with open trade but no valid same-day last executable tick");
            return;
         }
         CloseTrade(g_last_tick,"SESSION_END");
         if(g_fatal_status!="") return;
      }
      ResetDay(day);
   }

   int minute=MinuteOfDay(tick.time);

   if(minute>=OR_START_MINUTE && minute<OR_END_MINUTE)
   {
      if(!g_range_finalized)
      {
         if(g_or_ticks==0)
         {
            g_or_ask_high=tick.ask;
            g_or_bid_low=tick.bid;
         }
         else
         {
            if(tick.ask>g_or_ask_high) g_or_ask_high=tick.ask;
            if(tick.bid<g_or_bid_low) g_or_bid_low=tick.bid;
         }
         g_or_ticks++;
      }
   }
   else if(minute>=OR_END_MINUTE && !g_range_finalized)
   {
      FinalizeOpeningRange();
   }

   if(g_in_trade)
   {
      ObservePath(tick);
      if(g_fatal_status!="") return;
      EvaluateStop(tick);
      if(g_fatal_status!="") return;
      if(g_in_trade && minute>=EOD_EXIT_MINUTE) CloseTrade(tick,"EOD");
   }
   else
   {
      EvaluateEntry(tick);
      if(g_fatal_status!="") return;
      if(g_in_trade)
      {
         EvaluateStop(tick);
         if(g_fatal_status!="") return;
         if(g_in_trade && minute>=EOD_EXIT_MINUTE) CloseTrade(tick,"EOD");
      }
   }

   g_last_tick=tick;
   g_have_last_tick=true;
   if((g_ticks_seen%250000)==0) WriteStats("PROGRESS");
}

void OnDeinit(const int reason)
{
   if(g_fatal_status=="" && g_in_trade)
   {
      if(g_have_last_tick)
      {
         CloseTrade(g_last_tick,"TEST_END");
      }
      else
      {
         SetFatal("FINAL_INVALID_LIFECYCLE","tester ended with open trade and no last tick");
      }
   }

   string final_status=(g_fatal_status=="" ? "FINAL" : g_fatal_status);
   WriteStats(final_status);

   if(g_trades_fh!=INVALID_HANDLE)
   {
      FileFlush(g_trades_fh);
      FileClose(g_trades_fh);
      g_trades_fh=INVALID_HANDLE;
   }
   if(g_stats_fh!=INVALID_HANDLE)
   {
      FileFlush(g_stats_fh);
      FileClose(g_stats_fh);
      g_stats_fh=INVALID_HANDLE;
   }

   PrintFormat("D053 V101 FINAL | status=%s | symbol=%s | range_days=%I64d | opened=%I64d | closed=%I64d | rows=%I64d | invalid_price=%I64d | invalid_risk=%I64d | pnl_fail=%I64d | path_fail=%I64d",
      final_status,_Symbol,g_range_days,g_trades_opened,g_trades_closed,g_csv_rows,
      g_invalid_price,g_invalid_risk,g_pnl_calc_failures,g_path_calc_failures);
}