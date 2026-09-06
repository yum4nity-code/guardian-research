#property strict
#property version "1.00"
#property description "D039 Inside-Day Breakout V0 - tick execution and native Trade Path telemetry"

// D039 V0 frozen research harness. NO ORDERS.
// Preregistration:
// research/campaigns/D039_INSIDE_DAY_BREAKOUT_V0_PREREGISTRATION_2026_09_07.md
// Trade Path contract:
// research/runner/TRADE_PATH_DATASET_SPEC.md
//
// Frozen strategy:
// - D-1 must be a strict inside day relative to D-2
// - next broker day: first executable tick break of D-1 high/low wins
// - long at observed ask, short at observed bid; gaps get observed worse price
// - initial stop at opposite D-1 extreme
// - one trade/setup/day, no reversal
// - no TP, partial, BE, trailing, indicator, direction or regime filter
// - exit stop or broker-day end/test end
// - FundedNext frozen cost model + 1.5x commission stress
// - native executable-side MFE/MAE and R milestone telemetry

input bool InpWriteCSV=true;

string EXPERIMENT_ID="D039-INSIDE-DAY-BREAKOUT-V0";
string SOURCE_NAME="D039_InsideDay_TickPath_M15_v1_00.mq5";
string SOURCE_VERSION="1.00";
string RUN_TOKEN="RUN";

int g_trades_fh=INVALID_HANDLE;
int g_stats_fh=INVALID_HANDLE;
string g_stats_name="";
string g_trades_name="";
string g_common_path="";

// Day/setup state
datetime g_day_start=0;
int g_day_key=0;
bool g_setup_active=false;
bool g_day_traded=false;
bool g_day_ambiguous=false;
bool g_day_reference_unusable=false;
double g_inside_high=0.0;
double g_inside_low=0.0;
double g_inside_range=0.0;
double g_mother_high=0.0;
double g_mother_low=0.0;

// Trade state
bool g_in_trade=false;
bool g_long=false;
datetime g_signal_time=0;
datetime g_entry_time=0;
long g_entry_msc=0;
double g_entry=0.0;
double g_stop=0.0;
double g_risk_money=0.0;
string g_trade_id="";

// Last executable tick
bool g_have_last_tick=false;
MqlTick g_last_tick;

// Native Trade Path
double g_mfe_r=0.0;
double g_mae_r=0.0;
datetime g_mfe_time=0;
datetime g_mae_time=0;
long g_mfe_msc=0;
long g_mae_msc=0;
double g_max_retrace_from_mfe=0.0;
double g_levels[5]={0.5,1.0,2.0,3.0,5.0};
bool g_reached[5];
datetime g_first_touch[5];
long g_first_touch_msc[5];
double g_mae_before[5];
double g_min_after[3];
double g_max_after[3];
bool g_after_initialized[3];
bool g_path_ambiguous=false;
string g_path_ambiguity_reason="";

// Counters
long g_ticks_seen=0;
long g_days_initialized=0;
long g_inside_setup_days=0;
long g_non_inside_days=0;
long g_reference_unusable_days=0;
long g_ambiguous_days=0;
long g_entry_signals=0;
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
long g_path_calc_failures=0;
long g_csv_rows=0;
long g_path_rows=0;
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

bool ValidPrice(double x)
{
   return (x>0.0 && MathIsValidNumber(x));
}

long TickMsc(const MqlTick &tick)
{
   return (tick.time_msc>0 ? tick.time_msc : ((long)tick.time)*1000);
}

string TimeMinute(datetime t)
{
   return (t>0 ? TimeToString(t,TIME_DATE|TIME_MINUTES) : "");
}

string TimeSecond(datetime t)
{
   return (t>0 ? TimeToString(t,TIME_DATE|TIME_SECONDS) : "");
}

string BoolText(bool x)
{
   return x ? "1" : "0";
}

string MaybeDouble(bool available,double value)
{
   return available ? DoubleToString(value,8) : "";
}

void SetFatal(string status,string message)
{
   if(g_fatal_status=="") g_fatal_status=status;
   PrintFormat("D039 V100 FATAL | %s | %s",status,message);
}

bool CurrentD1(datetime t,MqlRates &cur)
{
   int shift=iBarShift(_Symbol,PERIOD_D1,t,false);
   if(shift<0) return false;
   MqlRates a[];
   ArraySetAsSeries(a,true);
   if(CopyRates(_Symbol,PERIOD_D1,shift,1,a)!=1) return false;
   cur=a[0];
   return (cur.time>0);
}

bool CalcMoney1LotCore(double entry_px,double exit_px,bool long_side,double &pnl,bool &used_fallback,int &primary_err)
{
   used_fallback=false;
   primary_err=0;
   if(!ValidPrice(entry_px) || !ValidPrice(exit_px)) return false;

   ENUM_ORDER_TYPE ot=long_side?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   ResetLastError();
   if(OrderCalcProfit(ot,_Symbol,1.0,entry_px,exit_px,pnl) && MathIsValidNumber(pnl))
      return true;

   primary_err=GetLastError();

   if((StringFind(_Symbol,"EURUSD")>=0 || StringFind(_Symbol,"GBPUSD")>=0) && AssetClass()=="FOREX")
   {
      double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
      if(contract>0.0 && MathIsValidNumber(contract))
      {
         double delta=long_side ? (exit_px-entry_px) : (entry_px-exit_px);
         pnl=contract*delta;
         if(MathIsValidNumber(pnl))
         {
            used_fallback=true;
            return true;
         }
      }
   }
   return false;
}

bool RiskMoney(double entry_px,double stop_px,bool long_side,double &risk_money)
{
   double pnl=0.0;
   bool fallback=false;
   int err=0;
   if(!CalcMoney1LotCore(entry_px,stop_px,long_side,pnl,fallback,err))
   {
      PrintFormat("D039 V100 RISK CALC FAILED | symbol=%s | err=%d | entry=%.10f | stop=%.10f",
                  _Symbol,err,entry_px,stop_px);
      return false;
   }
   if(fallback) g_risk_fallbacks++;
   risk_money=MathAbs(pnl);
   return (risk_money>0.0 && MathIsValidNumber(risk_money));
}

bool PnlMoney(double entry_px,double exit_px,bool long_side,double &pnl)
{
   bool fallback=false;
   int err=0;
   if(!CalcMoney1LotCore(entry_px,exit_px,long_side,pnl,fallback,err))
   {
      PrintFormat("D039 V100 PNL CALC FAILED | symbol=%s | err=%d | entry=%.10f | exit=%.10f",
                  _Symbol,err,entry_px,exit_px);
      return false;
   }
   if(fallback) g_pnl_fallbacks++;
   return true;
}

bool PathR(double exit_px,double &r)
{
   double pnl=0.0;
   bool fallback=false;
   int err=0;
   if(!CalcMoney1LotCore(g_entry,exit_px,g_long,pnl,fallback,err))
   {
      PrintFormat("D039 V100 PATH CALC FAILED | symbol=%s | err=%d | entry=%.10f | exit=%.10f",
                  _Symbol,err,g_entry,exit_px);
      return false;
   }
   if(!(g_risk_money>0.0) || !MathIsValidNumber(g_risk_money)) return false;
   r=pnl/g_risk_money;
   return MathIsValidNumber(r);
}

double CommissionUSD1Lot(double exit_px)
{
   if(!ValidPrice(g_entry) || !ValidPrice(exit_px)) return -1.0;
   string c=AssetClass();
   if(c=="FOREX") return 10.0;

   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract<=0.0 || !MathIsValidNumber(contract)) return -1.0;

   double rate=(c=="METAL" ? 0.000016 : 0.0004);
   double value=contract*g_entry*rate + contract*exit_px*rate;
   return (value>=0.0 && MathIsValidNumber(value)) ? value : -1.0;
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
   g_path_ambiguous=false;
   g_path_ambiguity_reason="";
   for(int i=0;i<5;i++)
   {
      g_reached[i]=false;
      g_first_touch[i]=0;
      g_first_touch_msc[i]=0;
      g_mae_before[i]=0.0;
   }
   for(int i=0;i<3;i++)
   {
      g_min_after[i]=0.0;
      g_max_after[i]=0.0;
      g_after_initialized[i]=false;
   }
}

void ResetTrade()
{
   g_in_trade=false;
   g_long=false;
   g_signal_time=0;
   g_entry_time=0;
   g_entry_msc=0;
   g_entry=0.0;
   g_stop=0.0;
   g_risk_money=0.0;
   g_trade_id="";
   ResetPath();
}

void ResetDay()
{
   g_day_start=0;
   g_day_key=0;
   g_setup_active=false;
   g_day_traded=false;
   g_day_ambiguous=false;
   g_day_reference_unusable=false;
   g_inside_high=0.0;
   g_inside_low=0.0;
   g_inside_range=0.0;
   g_mother_high=0.0;
   g_mother_low=0.0;
}

void ObservePath(const MqlTick &tick)
{
   if(!g_in_trade || g_fatal_status!="") return;
   double liquidation=g_long ? tick.bid : tick.ask;
   if(!ValidPrice(liquidation))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid executable liquidation price during path observation");
      return;
   }

   double current_r=0.0;
   if(!PathR(liquidation,current_r))
   {
      g_path_calc_failures++;
      SetFatal("FINAL_INVALID_PATH_CALC","cannot calculate executable-side path R");
      return;
   }

   long tmsc=TickMsc(tick);
   if(current_r>g_mfe_r)
   {
      g_mfe_r=current_r;
      g_mfe_time=tick.time;
      g_mfe_msc=tmsc;
   }
   double adverse=-current_r;
   if(adverse>g_mae_r)
   {
      g_mae_r=adverse;
      g_mae_time=tick.time;
      g_mae_msc=tmsc;
   }

   double retrace=g_mfe_r-current_r;
   if(retrace>g_max_retrace_from_mfe) g_max_retrace_from_mfe=retrace;

   for(int i=0;i<5;i++)
   {
      if(!g_reached[i] && current_r>=g_levels[i])
      {
         g_reached[i]=true;
         g_first_touch[i]=tick.time;
         g_first_touch_msc[i]=tmsc;
         g_mae_before[i]=g_mae_r;
      }
   }

   for(int j=0;j<3;j++)
   {
      int level_index=j+1;
      if(g_reached[level_index])
      {
         if(!g_after_initialized[j])
         {
            g_min_after[j]=current_r;
            g_max_after[j]=current_r;
            g_after_initialized[j]=true;
         }
         else
         {
            if(current_r<g_min_after[j]) g_min_after[j]=current_r;
            if(current_r>g_max_after[j]) g_max_after[j]=current_r;
         }
      }
   }
}

bool LoadDaySetup(datetime t,const MqlRates &cur)
{
   g_day_start=cur.time;
   g_day_key=DateKey(cur.time);
   g_days_initialized++;

   int shift=iBarShift(_Symbol,PERIOD_D1,t,false);
   if(shift<0)
   {
      g_day_reference_unusable=true;
      g_reference_unusable_days++;
      return true;
   }

   MqlRates refs[];
   ArraySetAsSeries(refs,true);
   if(CopyRates(_Symbol,PERIOD_D1,shift+1,2,refs)!=2)
   {
      g_day_reference_unusable=true;
      g_reference_unusable_days++;
      PrintFormat("D039 V100 SKIP_REFERENCE_UNAVAILABLE | symbol=%s | day=%s",_Symbol,TimeToString(cur.time,TIME_DATE));
      return true;
   }

   for(int i=0;i<2;i++)
   {
      if(refs[i].time<=0 || refs[i].time>=cur.time ||
         !ValidPrice(refs[i].high) || !ValidPrice(refs[i].low) || refs[i].high<=refs[i].low)
      {
         g_day_reference_unusable=true;
         g_reference_unusable_days++;
         PrintFormat("D039 V100 SKIP_REFERENCE_UNUSABLE | symbol=%s | day=%s | ref_index=%d | ref_time=%s | high=%.10f | low=%.10f",
                     _Symbol,TimeToString(cur.time,TIME_DATE),i+1,TimeToString(refs[i].time,TIME_DATE),refs[i].high,refs[i].low);
         return true;
      }
   }

   bool inside=(refs[0].high<refs[1].high && refs[0].low>refs[1].low);
   if(!inside)
   {
      g_non_inside_days++;
      return true;
   }

   g_inside_high=refs[0].high;
   g_inside_low=refs[0].low;
   g_inside_range=g_inside_high-g_inside_low;
   g_mother_high=refs[1].high;
   g_mother_low=refs[1].low;
   if(!(g_inside_range>0.0) || !MathIsValidNumber(g_inside_range))
   {
      g_day_reference_unusable=true;
      g_reference_unusable_days++;
      return true;
   }

   g_setup_active=true;
   g_inside_setup_days++;
   return true;
}

void WriteStats(string status)
{
   if(g_stats_fh==INVALID_HANDLE) return;
   FileWrite(g_stats_fh,status,SOURCE_NAME,SOURCE_VERSION,RUN_TOKEN,
      g_ticks_seen,g_days_initialized,g_inside_setup_days,g_non_inside_days,g_reference_unusable_days,g_ambiguous_days,
      g_entry_signals,g_trades_opened,g_trades_closed,g_stop_exits,g_eod_exits,g_test_end_exits,
      g_invalid_price,g_invalid_risk,g_risk_fallbacks,g_pnl_fallbacks,g_risk_calc_failures,g_pnl_calc_failures,
      g_path_calc_failures,g_csv_rows,g_path_rows,_Symbol,EnumToString(_Period),AssetClass(),CommissionRule(),g_fatal_status,
      g_trades_name,g_stats_name,g_common_path+g_trades_name,g_common_path+g_stats_name);
   FileFlush(g_stats_fh);
}

void CloseTrade(datetime exit_time,long exit_msc,double exit_px,string why)
{
   if(!g_in_trade) return;
   if(!ValidPrice(g_entry) || !ValidPrice(g_stop) || !ValidPrice(exit_px))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","entry/stop/exit invalid at close");
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
   if(!PnlMoney(g_entry,exit_px,g_long,pnl))
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
   double stress_r=gross_r-1.5*commission_r;
   if(!MathIsValidNumber(gross_r) || !MathIsValidNumber(commission_r) || !MathIsValidNumber(net_r) || !MathIsValidNumber(stress_r))
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
         RUN_TOKEN,_Symbol,AssetClass(),CommissionRule(),IntegerToString(g_day_key),TimeMinute(g_day_start),
         DoubleToString(g_inside_high,_Digits),DoubleToString(g_inside_low,_Digits),DoubleToString(g_inside_range,_Digits),
         DoubleToString(g_mother_high,_Digits),DoubleToString(g_mother_low,_Digits),
         g_long?"LONG":"SHORT",TimeMinute(g_signal_time),TimeMinute(g_entry_time),TimeMinute(exit_time),
         DoubleToString(g_entry,_Digits),DoubleToString(g_stop,_Digits),DoubleToString(exit_px,_Digits),
         DoubleToString(MathAbs(g_entry-g_stop),_Digits),DoubleToString(g_risk_money,8),DoubleToString(gross_r,8),
         DoubleToString(commission_usd,8),DoubleToString(commission_r,8),DoubleToString(net_r,8),DoubleToString(stress_r,8),why,g_trade_id,
         DoubleToString(g_mfe_r,8),DoubleToString(g_mae_r,8),TimeSecond(g_mfe_time),TimeSecond(g_mae_time),
         (g_mfe_msc>0?DoubleToString(time_to_mfe,6):""),(g_mae_msc>0?DoubleToString(time_to_mae,6):""),DoubleToString(g_max_retrace_from_mfe,8),
         BoolText(g_reached[0]),TimeSecond(g_first_touch[0]),(g_reached[0]?DoubleToString(((double)(g_first_touch_msc[0]-g_entry_msc))/60000.0,6):""),MaybeDouble(g_reached[0],g_mae_before[0]),
         BoolText(g_reached[1]),TimeSecond(g_first_touch[1]),(g_reached[1]?DoubleToString(((double)(g_first_touch_msc[1]-g_entry_msc))/60000.0,6):""),MaybeDouble(g_reached[1],g_mae_before[1]),
         BoolText(g_reached[2]),TimeSecond(g_first_touch[2]),(g_reached[2]?DoubleToString(((double)(g_first_touch_msc[2]-g_entry_msc))/60000.0,6):""),MaybeDouble(g_reached[2],g_mae_before[2]),
         BoolText(g_reached[3]),TimeSecond(g_first_touch[3]),(g_reached[3]?DoubleToString(((double)(g_first_touch_msc[3]-g_entry_msc))/60000.0,6):""),MaybeDouble(g_reached[3],g_mae_before[3]),
         BoolText(g_reached[4]),TimeSecond(g_first_touch[4]),(g_reached[4]?DoubleToString(((double)(g_first_touch_msc[4]-g_entry_msc))/60000.0,6):""),MaybeDouble(g_reached[4],g_mae_before[4]),
         MaybeDouble(g_after_initialized[0],g_min_after[0]),MaybeDouble(g_after_initialized[0],g_max_after[0]),
         MaybeDouble(g_after_initialized[1],g_min_after[1]),MaybeDouble(g_after_initialized[1],g_max_after[1]),
         MaybeDouble(g_after_initialized[2],g_min_after[2]),MaybeDouble(g_after_initialized[2],g_max_after[2]),
         BoolText(g_path_ambiguous),g_path_ambiguity_reason);
      FileFlush(g_trades_fh);
      g_csv_rows++;
      g_path_rows++;
   }

   g_trades_closed++;
   if(why=="STOP") g_stop_exits++;
   else if(why=="EOD") g_eod_exits++;
   else if(why=="TEST_END") g_test_end_exits++;
   ResetTrade();
}

void OpenTrade(const MqlTick &tick,bool long_side)
{
   g_entry_signals++;
   g_long=long_side;
   g_signal_time=tick.time;
   g_entry_time=tick.time;
   g_entry_msc=TickMsc(tick);
   g_entry=g_long ? tick.ask : tick.bid;
   g_stop=g_long ? g_inside_low : g_inside_high;

   if(!ValidPrice(g_entry) || !ValidPrice(g_stop))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","entry or initial stop invalid");
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

void EvaluateStop(const MqlTick &tick)
{
   if(!g_in_trade || g_fatal_status!="") return;
   if(g_long)
   {
      if(tick.bid<=g_stop)
         CloseTrade(tick.time,TickMsc(tick),tick.bid,"STOP");
   }
   else
   {
      if(tick.ask>=g_stop)
         CloseTrade(tick.time,TickMsc(tick),tick.ask,"STOP");
   }
}

void EvaluateEntry(const MqlTick &tick)
{
   if(g_in_trade || g_day_traded || g_day_ambiguous || !g_setup_active || g_day_reference_unusable) return;
   bool long_hit=(tick.ask>=g_inside_high);
   bool short_hit=(tick.bid<=g_inside_low);
   if(long_hit && short_hit)
   {
      g_day_ambiguous=true;
      g_ambiguous_days++;
      PrintFormat("D039 V100 AMBIGUOUS SAME TICK | symbol=%s | day=%d | bid=%.10f | ask=%.10f | high=%.10f | low=%.10f",
                  _Symbol,g_day_key,tick.bid,tick.ask,g_inside_high,g_inside_low);
      return;
   }
   if(long_hit) OpenTrade(tick,true);
   else if(short_hit) OpenTrade(tick,false);
}

int OnInit()
{
   if(_Period!=PERIOD_M15)
   {
      PrintFormat("D039 V100 FATAL wrong timeframe | got=%s | required=PERIOD_M15",EnumToString(_Period));
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!InpWriteCSV)
   {
      Print("D039 V100 FATAL InpWriteCSV must remain true.");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!IsAllowedSymbol())
   {
      PrintFormat("D039 V100 FATAL symbol outside frozen universe | %s",_Symbol);
      return INIT_PARAMETERS_INCORRECT;
   }
   if(AccountInfoString(ACCOUNT_CURRENCY)!="USD")
   {
      PrintFormat("D039 V100 FATAL account currency must be USD | got=%s",AccountInfoString(ACCOUNT_CURRENCY));
      return INIT_PARAMETERS_INCORRECT;
   }

   string sym=CleanSymbol();
   g_stats_name=StringFormat("D039_V100_RUN_%s_STATS.csv",sym);
   g_trades_name=StringFormat("D039_V100_RUN_%s_TRADES.csv",sym);
   g_common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";

   g_stats_fh=FileOpen(g_stats_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_stats_fh==INVALID_HANDLE)
   {
      PrintFormat("D039 V100 FATAL cannot open STATS | err=%d | %s%s",GetLastError(),g_common_path,g_stats_name);
      return INIT_FAILED;
   }
   FileWrite(g_stats_fh,"status","source_name","source_version","run_stage","ticks_seen","days_initialized","inside_setup_days",
      "non_inside_days","reference_unusable_days","ambiguous_days","entry_signals","trades_opened","trades_closed","stop_exits",
      "eod_exits","test_end_exits","invalid_price","invalid_risk","risk_fallbacks","pnl_fallbacks","risk_calc_failures",
      "pnl_calc_failures","path_calc_failures","csv_trade_rows","path_rows","symbol","timeframe","asset_class","commission_rule",
      "fatal_status","trades_name","stats_name","trades_csv_fullpath","stats_csv_fullpath");
   WriteStats("INIT");

   g_trades_fh=FileOpen(g_trades_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_trades_fh==INVALID_HANDLE)
   {
      WriteStats("FATAL_TRADES_OPEN");
      PrintFormat("D039 V100 FATAL cannot open TRADES | err=%d | %s%s",GetLastError(),g_common_path,g_trades_name);
      FileClose(g_stats_fh); g_stats_fh=INVALID_HANDLE;
      return INIT_FAILED;
   }

   FileWrite(g_trades_fh,
      "run_stage","symbol","asset_class","commission_rule","day_key","broker_day_start","inside_high","inside_low","inside_range",
      "mother_high","mother_low","side","signal_time","entry_time","exit_time","entry","initial_stop","exit","initial_risk_price","risk_money_1lot_usd",
      "gross_r","commission_usd_1lot","commission_r","net_r","net_r_commission_x1_5","exit_reason","trade_id",
      "mfe_r","mae_r","mfe_time","mae_time","time_to_mfe_minutes","time_to_mae_minutes","max_retracement_from_mfe_r",
      "reached_0_5r","first_touch_0_5r_time","time_to_0_5r_minutes","mae_before_0_5r",
      "reached_1r","first_touch_1r_time","time_to_1r_minutes","mae_before_1r",
      "reached_2r","first_touch_2r_time","time_to_2r_minutes","mae_before_2r",
      "reached_3r","first_touch_3r_time","time_to_3r_minutes","mae_before_3r",
      "reached_5r","first_touch_5r_time","time_to_5r_minutes","mae_before_5r",
      "min_r_after_first_1r_before_exit","max_r_after_first_1r_before_exit",
      "min_r_after_first_2r_before_exit","max_r_after_first_2r_before_exit",
      "min_r_after_first_3r_before_exit","max_r_after_first_3r_before_exit",
      "path_ambiguous","path_ambiguity_reason");
   FileFlush(g_trades_fh);
   WriteStats("READY");

   ResetDay();
   ResetTrade();
   PrintFormat("D039 V100 READY | source=%s | symbol=%s | Model0 tick execution | strict inside day | native Trade Path | NO ORDERS",SOURCE_NAME,_Symbol);
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
      SetFatal("FINAL_INVALID_PRICE","invalid tick bid/ask");
      return;
   }
   g_ticks_seen++;

   MqlRates cur;
   if(!CurrentD1(tick.time,cur))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","cannot resolve current broker D1 bar");
      return;
   }

   if(g_day_start==0 || cur.time!=g_day_start)
   {
      if(g_day_start!=0 && g_in_trade)
      {
         if(!g_have_last_tick)
         {
            SetFatal("FINAL_INVALID_LIFECYCLE","day changed with open trade but no prior executable tick");
            return;
         }
         double eod_px=g_long ? g_last_tick.bid : g_last_tick.ask;
         CloseTrade(g_last_tick.time,TickMsc(g_last_tick),eod_px,"EOD");
         if(g_fatal_status!="") return;
      }
      ResetDay();
      if(!LoadDaySetup(tick.time,cur)) return;
   }

   if(g_in_trade)
   {
      ObservePath(tick);
      if(g_fatal_status!="") return;
      EvaluateStop(tick);
   }
   else
   {
      EvaluateEntry(tick);
      if(g_fatal_status!="") return;
      if(g_in_trade) EvaluateStop(tick);
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
         double px=g_long ? g_last_tick.bid : g_last_tick.ask;
         CloseTrade(g_last_tick.time,TickMsc(g_last_tick),px,"TEST_END");
      }
      else
      {
         SetFatal("FINAL_INVALID_LIFECYCLE","tester ended with open trade and no executable last tick");
      }
   }

   string final_status=(g_fatal_status=="" ? "FINAL" : g_fatal_status);
   WriteStats(final_status);
   if(g_trades_fh!=INVALID_HANDLE){FileFlush(g_trades_fh);FileClose(g_trades_fh);g_trades_fh=INVALID_HANDLE;}
   if(g_stats_fh!=INVALID_HANDLE){FileFlush(g_stats_fh);FileClose(g_stats_fh);g_stats_fh=INVALID_HANDLE;}

   PrintFormat("D039 V100 FINAL | status=%s | symbol=%s | ticks=%I64d | inside_days=%I64d | opened=%I64d | closed=%I64d | rows=%I64d | path_rows=%I64d | invalid_price=%I64d | invalid_risk=%I64d | pnl_failures=%I64d | path_failures=%I64d",
      final_status,_Symbol,g_ticks_seen,g_inside_setup_days,g_trades_opened,g_trades_closed,g_csv_rows,g_path_rows,g_invalid_price,g_invalid_risk,g_pnl_calc_failures,g_path_calc_failures);
}
