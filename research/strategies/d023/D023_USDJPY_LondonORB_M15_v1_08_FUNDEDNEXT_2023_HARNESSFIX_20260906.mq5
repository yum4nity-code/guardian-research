#property strict
#property version "1.08"
#property description "D023 USDJPY London ORB M15 - FundedNext 2023 confirmation HARNESSFIX - no orders"

// D023 frozen London ORB V0.
// NO strategy tuning here.
// v1.08 HARNESSFIX changes observability/output only:
//   - fixes FILE_COMMON display path escaping;
//   - hard-fails wrong timeframe or disabled CSV output;
//   - writes STATS INIT before opening TRADES, then READY after both outputs exist;
//   - logs exact source/version/symbol/timeframe/cost/frozen session semantics;
//   - keeps deterministic v1.08 TRADES/STATS filenames and flushes every status/trade row.
// Changes vs v1.02 are conformance only:
//   - FundedNext server clock (GMT+2 / GMT+3 with US DST schedule)
//   - Europe/London DST-aware conversion
//   - FundedNext Forex commission written in R
//   - isolated CSV filename (no accumulation with old D023 files)
//
// UNTOUCHED CONFIRMATION RUN ONLY:
//   USDJPY, M15, Every tick
//   2023.01.02 -> 2023.12.29
//
// This version refuses to process any bar outside calendar year 2023.
// Frozen pass gates are evaluated AFTER the CSV is returned:
//   n >= 150
//   mean net R > 0
//   net PF >= 1.10
//   5-day moving-block bootstrap lower 5% bound of weekday daily mean R > 0
//   total net R remains positive with commission multiplied by 1.5
//
// No manager tuning, no entry filter, no direction filter, no parameter search.

enum FN_COMMISSION_MODEL
  {
   FN_STELLAR_1STEP_2STEP = 0, // current FundedNext general rules: USD 5 / lot / side on Forex
   FN_STELLAR_LITE        = 1, // USD 7 / lot / side on Forex
   FN_STELLAR_INSTANT     = 2, // general-rules interpretation: USD 7 / lot / side
   FN_CUSTOM_PER_SIDE     = 3
  };

input FN_COMMISSION_MODEL InpFundedNextModel=FN_STELLAR_1STEP_2STEP;
input double InpCustomForexCommissionUSDPerLotSide=5.00;
input bool   InpWriteCSV=true;
input bool   InpRequireUSDJPY=true;

int g_fh=INVALID_HANDLE;
int g_stats_fh=INVALID_HANDLE;
datetime g_last_closed=0;
string g_day="";
double g_or_hi=0.0,g_or_lo=0.0,g_entry=0.0,g_sl=0.0,g_risk=0.0;
int g_or_count=0;
bool g_signalled=false,g_in_trade=false,g_is_long=false;
datetime g_entry_time=0;

// Diagnostic counters only. They do not affect trading logic.
long g_bars_seen=0;
long g_bars_2023=0;
long g_weekday_bars_2023=0;
int  g_days_seen=0;
int  g_days_or_complete=0;
int  g_breakout_signals=0;
int  g_trades_opened=0;
int  g_trades_closed=0;
int  g_stop_exits=0;
int  g_time_exits=0;
int  g_invalid_risk_signals=0;
int  g_csv_rows=0;
bool g_or_complete_counted=false;

// ---------- calendar ----------
bool IsLeap(int y){return ((y%4)==0 && ((y%100)!=0 || (y%400)==0));}

int DaysInMonth(int y,int m)
{
   if(m==2) return IsLeap(y)?29:28;
   if(m==4 || m==6 || m==9 || m==11) return 30;
   return 31;
}

datetime MakeDT(int y,int m,int d,int hh=0,int mm=0,int ss=0)
{
   MqlDateTime x;
   ZeroMemory(x);
   x.year=y; x.mon=m; x.day=d; x.hour=hh; x.min=mm; x.sec=ss;
   return StructToTime(x);
}

int WeekdayOfDate(int y,int m,int d)
{
   MqlDateTime x;
   TimeToStruct(MakeDT(y,m,d,12,0,0),x);
   return x.day_of_week;
}

int NthSunday(int y,int m,int nth)
{
   int first_wd=WeekdayOfDate(y,m,1);
   int first_sunday=1+((7-first_wd)%7);
   return first_sunday+7*(nth-1);
}

int LastSunday(int y,int m)
{
   int last=DaysInMonth(y,m);
   int wd=WeekdayOfDate(y,m,last);
   return last-wd;
}

// FundedNext explicitly switches MetaTrader server time with US DST.
// Standard: GMT+2. US DST: GMT+3.
// Monday-Friday ORB processing means the exact Sunday transition hour
// cannot affect an ORB trading day.
int FundedNextServerUTCOffsetHours(datetime server_t)
{
   MqlDateTime s;
   TimeToStruct(server_t,s);
   int y=s.year;

   int us_start=NthSunday(y,3,2); // second Sunday in March
   int us_end=NthSunday(y,11,1);  // first Sunday in November

   bool dst=false;
   if(s.mon>3 && s.mon<11) dst=true;
   else if(s.mon==3 && s.day>=us_start) dst=true;
   else if(s.mon==11 && s.day<us_end) dst=true;

   return dst?3:2;
}

// London: UTC in winter, UTC+1 in British Summer Time.
int LondonUTCOffsetHours(datetime server_t)
{
   MqlDateTime s;
   TimeToStruct(server_t,s);
   int y=s.year;

   int uk_start=LastSunday(y,3);
   int uk_end=LastSunday(y,10);

   bool dst=false;
   if(s.mon>3 && s.mon<10) dst=true;
   else if(s.mon==3 && s.day>=uk_start) dst=true;
   else if(s.mon==10 && s.day<uk_end) dst=true;

   return dst?1:0;
}

datetime LondonTime(datetime server_t)
{
   int diff=FundedNextServerUTCOffsetHours(server_t)-LondonUTCOffsetHours(server_t);
   return server_t-diff*3600;
}

int LMin(datetime server_t)
{
   MqlDateTime d;
   TimeToStruct(LondonTime(server_t),d);
   return d.hour*60+d.min;
}

int LWeekday(datetime server_t)
{
   MqlDateTime d;
   TimeToStruct(LondonTime(server_t),d);
   return d.day_of_week;
}

string LDay(datetime server_t)
{
   MqlDateTime d;
   TimeToStruct(LondonTime(server_t),d);
   return StringFormat("%04d-%02d-%02d",d.year,d.mon,d.day);
}

// ---------- costs ----------
double ForexCommissionPerLotSideUSD()
{
   if(InpFundedNextModel==FN_STELLAR_1STEP_2STEP) return 5.00;
   if(InpFundedNextModel==FN_STELLAR_LITE)        return 7.00;
   if(InpFundedNextModel==FN_STELLAR_INSTANT)     return 7.00;
   return MathMax(0.0,InpCustomForexCommissionUSDPerLotSide);
}

string CommissionModelName()
{
   if(InpFundedNextModel==FN_STELLAR_1STEP_2STEP) return "STELLAR_1STEP_2STEP";
   if(InpFundedNextModel==FN_STELLAR_LITE)        return "STELLAR_LITE";
   if(InpFundedNextModel==FN_STELLAR_INSTANT)     return "STELLAR_INSTANT";
   return "CUSTOM_PER_SIDE";
}

double Spr(const MqlRates &b){return (double)b.spread*_Point;}

double EntryPx(bool long_side,const MqlRates &cur)
{
   return long_side ? cur.open+Spr(cur) : cur.open;
}

double ExitPx(bool long_side,const MqlRates &b)
{
   return long_side ? b.close : b.close+Spr(b);
}

bool StopHit(bool long_side,const MqlRates &b,double stop_px)
{
   return long_side ? b.low<=stop_px : b.high+Spr(b)>=stop_px;
}

double CommissionR()
{
   if(g_risk<=0.0 || g_entry<=0.0 || g_sl<=0.0) return -1.0;

   double risk_money=0.0;
   ENUM_ORDER_TYPE ot=g_is_long?ORDER_TYPE_BUY:ORDER_TYPE_SELL;

   // Profit/loss of a 1-lot move from entry to initial stop,
   // automatically converted by the tester/account into account currency.
   if(!OrderCalcProfit(ot,_Symbol,1.0,g_entry,g_sl,risk_money))
      return -1.0;

   risk_money=MathAbs(risk_money);
   if(risk_money<=0.0) return -1.0;

   // FundedNext general rules quote Forex commission PER SIDE.
   double commission_round_trip=2.0*ForexCommissionPerLotSideUSD();
   return commission_round_trip/risk_money;
}

// ---------- state ----------
void ResetDay(string d)
{
   g_day=d;
   g_days_seen++;
   g_or_complete_counted=false;
   g_or_hi=0.0;
   g_or_lo=0.0;
   g_or_count=0;
   g_signalled=false;
   g_in_trade=false;
   g_entry=0.0;
   g_sl=0.0;
   g_risk=0.0;
   g_entry_time=0;
}

void WriteTrade(datetime xt,double xp,string why)
{
   double pnl=g_is_long?xp-g_entry:g_entry-xp;
   double gross_r=(g_risk>0.0?pnl/g_risk:0.0);
   double commission_r=CommissionR();
   double net_r=(commission_r>=0.0?gross_r-commission_r:gross_r);

   if(g_fh!=INVALID_HANDLE)
   {
      FileWrite(g_fh,
         g_day,
         _Symbol,
         CommissionModelName(),
         DoubleToString(ForexCommissionPerLotSideUSD(),2),
         g_is_long?"LONG":"SHORT",
         TimeToString(g_entry_time,TIME_DATE|TIME_MINUTES),
         TimeToString(xt,TIME_DATE|TIME_MINUTES),
         TimeToString(LondonTime(g_entry_time),TIME_DATE|TIME_MINUTES),
         TimeToString(LondonTime(xt),TIME_DATE|TIME_MINUTES),
         IntegerToString(FundedNextServerUTCOffsetHours(g_entry_time)),
         IntegerToString(LondonUTCOffsetHours(g_entry_time)),
         DoubleToString(g_or_hi,_Digits),
         DoubleToString(g_or_lo,_Digits),
         DoubleToString(g_entry,_Digits),
         DoubleToString(g_sl,_Digits),
         DoubleToString(xp,_Digits),
         DoubleToString(g_risk,_Digits),
         DoubleToString(gross_r,8),
         DoubleToString(commission_r,8),
         DoubleToString(net_r,8),
         why
      );
      FileFlush(g_fh);
      g_csv_rows++;
   }

   g_trades_closed++;
   if(why=="STOP") g_stop_exits++;
   if(why=="TIME_1600") g_time_exits++;
   g_in_trade=false;
}

int OnInit()
{
   if(InpRequireUSDJPY && StringFind(_Symbol,"USDJPY")<0)
   {
      Print("D023 v1.08 FundedNext: USDJPY only.");
      return INIT_PARAMETERS_INCORRECT;
   }

   // Harness guard only: strategy logic itself always reads PERIOD_M15,
   // but a wrong tester timeframe would create ambiguous provenance.
   if(_Period!=PERIOD_M15)
   {
      PrintFormat("D023 V108 FATAL: wrong tester timeframe | got=%s | required=M15",EnumToString(_Period));
      return INIT_PARAMETERS_INCORRECT;
   }

   // A confirmation harness without outputs is not a valid run.
   if(!InpWriteCSV)
   {
      Print("D023 V108 FATAL: InpWriteCSV must remain true for confirmation/smoke runs.");
      return INIT_PARAMETERS_INCORRECT;
   }

   string common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";
   string trades_name="D023_V108_USDJPY_2023_TRADES.csv";
   string stats_name ="D023_V108_USDJPY_2023_STATS.csv";

   // Create STATS first so even a later TRADES-open failure leaves evidence.
   g_stats_fh=FileOpen(stats_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_stats_fh==INVALID_HANDLE)
   {
      PrintFormat("D023 V108 FATAL: cannot create STATS CSV | err=%d | path=%s%s",
                  GetLastError(),common_path,stats_name);
      return INIT_FAILED;
   }

   FileWrite(g_stats_fh,
      "status","source_name","source_version","bars_seen","bars_2023","weekday_bars_2023","days_seen",
      "or_complete_days","breakout_signals","trades_opened","trades_closed",
      "stop_exits","time_exits","invalid_risk_signals","csv_trade_rows",
      "symbol","timeframe","fundednext_model","commission_usd_per_lot_side",
      "trades_csv_fullpath","stats_csv_fullpath"
   );

   FileWrite(g_stats_fh,
      "INIT","D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5","1.08",0,0,0,0,0,0,0,0,0,0,0,0,
      _Symbol,EnumToString(_Period),CommissionModelName(),DoubleToString(ForexCommissionPerLotSideUSD(),2),
      common_path+trades_name,common_path+stats_name
   );
   FileFlush(g_stats_fh);

   g_fh=FileOpen(trades_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_fh==INVALID_HANDLE)
   {
      int err=GetLastError();
      FileWrite(g_stats_fh,
         "FATAL_TRADES_OPEN","D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5","1.08",0,0,0,0,0,0,0,0,0,0,0,0,
         _Symbol,EnumToString(_Period),CommissionModelName(),DoubleToString(ForexCommissionPerLotSideUSD(),2),
         common_path+trades_name,common_path+stats_name
      );
      FileFlush(g_stats_fh);
      PrintFormat("D023 V108 FATAL: cannot create TRADES CSV | err=%d | path=%s%s",
                  err,common_path,trades_name);
      FileClose(g_stats_fh);
      g_stats_fh=INVALID_HANDLE;
      return INIT_FAILED;
   }

   FileWrite(g_fh,
      "london_day","symbol",
      "fundednext_model","commission_usd_per_lot_side",
      "side",
      "entry_time_server","exit_time_server",
      "entry_time_london","exit_time_london",
      "server_utc_offset_h","london_utc_offset_h",
      "or_high","or_low","entry","stop","exit","risk_price",
      "gross_r","commission_r","net_r","exit_reason"
   );
   FileFlush(g_fh);

   FileWrite(g_stats_fh,
      "READY","D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5","1.08",0,0,0,0,0,0,0,0,0,0,0,0,
      _Symbol,EnumToString(_Period),CommissionModelName(),DoubleToString(ForexCommissionPerLotSideUSD(),2),
      common_path+trades_name,common_path+stats_name
   );
   FileFlush(g_stats_fh);

   PrintFormat("D023 V108 SOURCE | source=D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5 | version=1.08 | symbol=%s | timeframe=%s | NO ORDERS",
               _Symbol,EnumToString(_Period));
   PrintFormat("D023 V108 FROZEN | London OR=08:00-09:00 | breakout=09:00-11:00 | entry=next M15 open executable side | stop=opposite OR edge | exit=stop or 16:00 London | max 1/day");
   PrintFormat("D023 V108 COST | model=%s | FX commission=%.2f USD/lot/side",
               CommissionModelName(),ForexCommissionPerLotSideUSD());
   PrintFormat("D023 V108 OUTPUT READY | trades=%s%s | stats=%s%s",
               common_path,trades_name,common_path,stats_name);

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   string common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";
   string trades_name="D023_V108_USDJPY_2023_TRADES.csv";
   string stats_name ="D023_V108_USDJPY_2023_STATS.csv";

   if(g_stats_fh!=INVALID_HANDLE)
   {
      FileWrite(g_stats_fh,
         "FINAL","D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5","1.08",
         g_bars_seen,g_bars_2023,g_weekday_bars_2023,g_days_seen,
         g_days_or_complete,g_breakout_signals,g_trades_opened,g_trades_closed,
         g_stop_exits,g_time_exits,g_invalid_risk_signals,g_csv_rows,
         _Symbol,EnumToString(_Period),CommissionModelName(),DoubleToString(ForexCommissionPerLotSideUSD(),2),
         common_path+trades_name,common_path+stats_name
      );
      FileFlush(g_stats_fh);
   }

   PrintFormat(
      "D023 V108 SUMMARY | deinit_reason=%d | bars_seen=%I64d | bars_2023=%I64d | weekday_bars=%I64d | days=%d | OR_complete_days=%d | breakouts=%d | opened=%d | closed=%d | STOP=%d | TIME=%d | invalid_risk=%d | csv_rows=%d | open_at_end=%s",
      reason,g_bars_seen,g_bars_2023,g_weekday_bars_2023,g_days_seen,g_days_or_complete,
      g_breakout_signals,g_trades_opened,g_trades_closed,g_stop_exits,g_time_exits,
      g_invalid_risk_signals,g_csv_rows,g_in_trade?"true":"false"
   );

   PrintFormat("D023 V108 FILES | trades=%s%s | stats=%s%s",
               common_path,trades_name,common_path,stats_name);

   if(g_fh!=INVALID_HANDLE)
   {
      FileFlush(g_fh);
      FileClose(g_fh);
      g_fh=INVALID_HANDLE;
   }
   if(g_stats_fh!=INVALID_HANDLE)
   {
      FileClose(g_stats_fh);
      g_stats_fh=INVALID_HANDLE;
   }
}

void OnTick()
{
   MqlRates r[];
   ArrayResize(r,2);
   ArraySetAsSeries(r,true);

   if(CopyRates(_Symbol,PERIOD_M15,0,2,r)!=2) return;

   MqlRates cur=r[0],b=r[1];

   // Count each newly closed M15 bar before applying the 2023 guard.
   if(b.time==g_last_closed) return;
   g_last_closed=b.time;
   g_bars_seen++;

   // Hard confirmation guard: no bar outside 2023 is inspected by the strategy.
   MqlDateTime sy;
   TimeToStruct(b.time,sy);
   if(sy.year!=2023) return;
   g_bars_2023++;

   string d=LDay(b.time);
   if(g_day=="") ResetDay(d);
   if(d!=g_day) ResetDay(d);

   int wd=LWeekday(b.time);
   if(wd==0 || wd==6) return;
   g_weekday_bars_2023++;

   int m=LMin(b.time);

   // Frozen opening range = 08:00, 08:15, 08:30, 08:45 London.
   if(m>=480 && m<540)
   {
      if(g_or_count==0)
      {
         g_or_hi=b.high;
         g_or_lo=b.low;
      }
      else
      {
         if(b.high>g_or_hi) g_or_hi=b.high;
         if(b.low<g_or_lo)  g_or_lo=b.low;
      }
      g_or_count++;
      if(g_or_count==4 && !g_or_complete_counted)
      {
         g_or_complete_counted=true;
         g_days_or_complete++;
      }
   }

   // Frozen exit = stop first, else 16:00 London session exit.
   if(g_in_trade)
   {
      if(StopHit(g_is_long,b,g_sl))
      {
         WriteTrade(b.time,g_sl,"STOP");
         return;
      }

      if(m==945) // closed 15:45-16:00 London bar
      {
         WriteTrade(b.time,ExitPx(g_is_long,b),"TIME_1600");
         return;
      }
   }

   // Frozen breakout search = first M15 close 09:00 <= t < 11:00 London.
   // Entry = next M15 bar open at executable side of observed spread.
   if(!g_in_trade && !g_signalled && g_or_count==4 && m>=540 && m<660)
   {
      bool lg=b.close>g_or_hi;
      bool sh=b.close<g_or_lo;

      if(lg||sh)
      {
         g_breakout_signals++;
         g_signalled=true;
         g_is_long=lg;
         g_entry=EntryPx(g_is_long,cur);
         g_sl=g_is_long?g_or_lo:g_or_hi;
         g_risk=g_is_long?g_entry-g_sl:g_sl-g_entry;

         if(g_risk>0.0)
         {
            g_in_trade=true;
            g_entry_time=cur.time;
            g_trades_opened++;
         }
         else
         {
            g_invalid_risk_signals++;
         }
      }
   }
}
