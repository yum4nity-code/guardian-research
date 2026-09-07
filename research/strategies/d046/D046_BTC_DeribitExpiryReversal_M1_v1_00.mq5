#property strict
#property version "1.00"
#property description "D046 BTC Deribit 08UTC expiry reversal unconditional screen V0"

input bool InpWriteCSV=true;

string EXPERIMENT_ID="D046-BTC-DERIBIT-08UTC-EXPIRY-REVERSAL-SCREEN-V0";
string SOURCE_NAME="D046_BTC_DeribitExpiryReversal_M1_v1_00.mq5";
string SOURCE_VERSION="1.00";
string RUN_TOKEN="RUN";

const double COMMISSION_BPS=8.0;
const double STRESS_COMMISSION_BPS=12.0;
const int MAX_BOUNDARY_DELAY_SECONDS=300;

int g_stats_fh=INVALID_HANDLE;
int g_trades_fh=INVALID_HANDLE;
string g_stats_name="";
string g_trades_name="";
string g_common_path="";

long g_ticks_seen=0;
long g_days_seen=0;
long g_transition_days_skipped=0;
long g_trades_opened=0;
long g_trades_closed=0;
long g_csv_trade_rows=0;
long g_invalid_price=0;
long g_invalid_risk=0;
long g_pnl_calc_failures=0;
long g_late_boundary_skips=0;
long g_forced_ineligible_closes=0;
string g_fatal_status="";

int g_utc_day_key=0;
bool g_pre_attempted=false;
bool g_post_attempted=false;
int g_leg=0; // 0 none, 1 PRE_SHORT, 2 POST_LONG
datetime g_entry_server=0;
datetime g_entry_utc=0;
double g_entry_price=0.0;
int g_entry_delay_seconds=0;
int g_entry_offset_hours=0;
string g_trade_id="";

bool g_have_last_tick=false;
MqlTick g_last_tick;

bool ValidPrice(double x)
{
   return (x>0.0 && MathIsValidNumber(x));
}

int DateKey(datetime t)
{
   MqlDateTime d;
   TimeToStruct(t,d);
   return d.year*10000+d.mon*100+d.day;
}

int SecondsOfDay(datetime t)
{
   MqlDateTime d;
   TimeToStruct(t,d);
   return d.hour*3600+d.min*60+d.sec;
}

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
   return (StringFind(_Symbol,"BTCUSD")>=0);
}

bool IsTransitionServerDate(int key)
{
   return (
      key==20240310 || key==20240311 ||
      key==20241103 || key==20241104 ||
      key==20250309 || key==20250310 ||
      key==20251102 || key==20251103 ||
      key==20260308 || key==20260309 ||
      key==20261101 || key==20261102
   );
}

int ServerUtcOffsetHours(datetime server_time)
{
   int key=DateKey(server_time);
   if((key>=20240311 && key<20241104) ||
      (key>=20250310 && key<20251103) ||
      (key>=20260309 && key<20261102))
      return 3;
   return 2;
}

datetime ServerToUtc(datetime server_time)
{
   return server_time-(datetime)(ServerUtcOffsetHours(server_time)*3600);
}

string IsoTime(datetime t)
{
   if(t<=0) return "";
   return TimeToString(t,TIME_DATE|TIME_SECONDS);
}

void SetFatal(string code,string message)
{
   if(g_fatal_status=="") g_fatal_status=code;
   PrintFormat("D046 V100 FATAL | %s | %s",code,message);
}

void WriteStats(string status)
{
   if(g_stats_fh==INVALID_HANDLE) return;
   FileWrite(g_stats_fh,status,SOURCE_NAME,SOURCE_VERSION,RUN_TOKEN,_Symbol,
      g_ticks_seen,g_days_seen,g_transition_days_skipped,g_trades_opened,g_trades_closed,g_csv_trade_rows,
      g_invalid_price,g_invalid_risk,g_pnl_calc_failures,g_late_boundary_skips,g_forced_ineligible_closes,
      g_fatal_status,g_trades_name,g_stats_name,g_common_path+g_trades_name,g_common_path+g_stats_name);
   FileFlush(g_stats_fh);
}

void ResetDay(int utc_day_key)
{
   g_utc_day_key=utc_day_key;
   g_pre_attempted=false;
   g_post_attempted=false;
   g_days_seen++;
}

void ResetLeg()
{
   g_leg=0;
   g_entry_server=0;
   g_entry_utc=0;
   g_entry_price=0.0;
   g_entry_delay_seconds=0;
   g_entry_offset_hours=0;
   g_trade_id="";
}

void OpenLeg(const MqlTick &tick,int leg,datetime utc_time,int delay_seconds)
{
   if(g_leg!=0 || g_fatal_status!="") return;
   double px=(leg==1 ? tick.bid : tick.ask);
   if(!ValidPrice(px))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid executable entry price");
      return;
   }
   g_leg=leg;
   g_entry_server=tick.time;
   g_entry_utc=utc_time;
   g_entry_price=px;
   g_entry_delay_seconds=delay_seconds;
   g_entry_offset_hours=ServerUtcOffsetHours(tick.time);
   string tag=(leg==1 ? "PRE_SHORT" : "POST_LONG");
   g_trade_id=StringFormat("%s_%d_%s",CleanSymbol(),g_utc_day_key,tag);
   g_trades_opened++;
}

void CloseLeg(const MqlTick &tick,datetime utc_time,int exit_delay_seconds,bool eligible,string reason)
{
   if(g_leg==0) return;
   double exit_px=(g_leg==1 ? tick.ask : tick.bid);
   if(!ValidPrice(g_entry_price) || !ValidPrice(exit_px))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid executable entry/exit price");
      ResetLeg();
      return;
   }

   double gross_bps=0.0;
   string leg_name="";
   string side="";
   if(g_leg==1)
   {
      gross_bps=(g_entry_price-exit_px)/g_entry_price*10000.0;
      leg_name="PRE_SHORT";
      side="SHORT";
   }
   else
   {
      gross_bps=(exit_px-g_entry_price)/g_entry_price*10000.0;
      leg_name="POST_LONG";
      side="LONG";
   }
   if(!MathIsValidNumber(gross_bps))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","non-finite gross bps");
      ResetLeg();
      return;
   }

   double net_bps=gross_bps-COMMISSION_BPS;
   double stress_bps=gross_bps-STRESS_COMMISSION_BPS;
   int exit_offset=ServerUtcOffsetHours(tick.time);

   if(g_trades_fh!=INVALID_HANDLE)
   {
      FileWrite(g_trades_fh,RUN_TOKEN,_Symbol,IntegerToString(g_utc_day_key),leg_name,side,
         IsoTime(g_entry_server),IsoTime(tick.time),IsoTime(g_entry_utc),IsoTime(utc_time),
         g_entry_offset_hours,exit_offset,
         DoubleToString(g_entry_price,_Digits),DoubleToString(exit_px,_Digits),
         DoubleToString(gross_bps,8),DoubleToString(COMMISSION_BPS,8),
         DoubleToString(net_bps,8),DoubleToString(stress_bps,8),
         g_entry_delay_seconds,exit_delay_seconds,(eligible?"1":"0"),reason,g_trade_id);
      FileFlush(g_trades_fh);
      g_csv_trade_rows++;
   }
   g_trades_closed++;
   if(!eligible) g_forced_ineligible_closes++;
   ResetLeg();
}

void ForceCloseIfNeeded(const MqlTick &tick,datetime utc_time,string reason)
{
   if(g_leg!=0) CloseLeg(tick,utc_time,0,false,reason);
}

int OnInit()
{
   if(!IsAllowedSymbol())
      return INIT_FAILED;

   ResetLeg();
   if(!InpWriteCSV) return INIT_SUCCEEDED;

   g_common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";
   string clean=CleanSymbol();
   g_stats_name=StringFormat("D046_V100_%s_%s_STATS.csv",RUN_TOKEN,clean);
   g_trades_name=StringFormat("D046_V100_%s_%s_TRADES.csv",RUN_TOKEN,clean);

   g_stats_fh=FileOpen(g_stats_name,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,';');
   g_trades_fh=FileOpen(g_trades_name,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,';');
   if(g_stats_fh==INVALID_HANDLE || g_trades_fh==INVALID_HANDLE)
      return INIT_FAILED;

   FileWrite(g_stats_fh,"status","source_name","source_version","run_stage","symbol",
      "ticks_seen","days_seen","transition_days_skipped","trades_opened","trades_closed","csv_trade_rows",
      "invalid_price","invalid_risk","pnl_calc_failures","late_boundary_skips","forced_ineligible_closes",
      "fatal_status","trades_file","stats_file","trades_path","stats_path");

   FileWrite(g_trades_fh,"run_stage","symbol","utc_day_key","leg","side",
      "entry_server_time","exit_server_time","entry_utc","exit_utc",
      "entry_server_utc_offset_hours","exit_server_utc_offset_hours",
      "entry_price","exit_price","gross_bps","commission_bps","net_bps","net_bps_commission_x1_5",
      "entry_delay_seconds","exit_delay_seconds","eligible","exclusion_reason","trade_id");

   WriteStats("INIT");
   WriteStats("READY");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(g_fatal_status!="") return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   if(!ValidPrice(tick.bid) || !ValidPrice(tick.ask) || tick.ask<tick.bid)
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid tick bid/ask");
      return;
   }

   g_ticks_seen++;
   g_last_tick=tick;
   g_have_last_tick=true;

   datetime utc=ServerToUtc(tick.time);
   int utc_key=DateKey(utc);

   if(g_utc_day_key==0)
      ResetDay(utc_key);
   else if(utc_key!=g_utc_day_key)
   {
      ForceCloseIfNeeded(tick,utc,"UTC_DAY_CHANGE_FORCE");
      ResetDay(utc_key);
   }

   if(IsTransitionServerDate(DateKey(tick.time)))
   {
      if(!g_pre_attempted || !g_post_attempted) g_transition_days_skipped++;
      g_pre_attempted=true;
      g_post_attempted=true;
      return;
   }

   int sod=SecondsOfDay(utc);
   const int T0700=7*3600;
   const int T0800=8*3600;
   const int T0900=9*3600;

   if(!g_pre_attempted && sod>=T0700)
   {
      g_pre_attempted=true;
      int delay=sod-T0700;
      if(delay<=MAX_BOUNDARY_DELAY_SECONDS && sod<T0800)
         OpenLeg(tick,1,utc,delay);
      else
         g_late_boundary_skips++;
   }

   if(sod>=T0800)
   {
      if(g_leg==1)
      {
         int delay=sod-T0800;
         bool ok=(delay<=MAX_BOUNDARY_DELAY_SECONDS);
         CloseLeg(tick,utc,delay,ok,(ok?"ELIGIBLE":"LATE_0800_EXIT"));
      }

      if(!g_post_attempted)
      {
         g_post_attempted=true;
         int delay=sod-T0800;
         if(delay<=MAX_BOUNDARY_DELAY_SECONDS && sod<T0900)
            OpenLeg(tick,2,utc,delay);
         else
            g_late_boundary_skips++;
      }
   }

   if(sod>=T0900 && g_leg==2)
   {
      int delay=sod-T0900;
      bool ok=(delay<=MAX_BOUNDARY_DELAY_SECONDS);
      CloseLeg(tick,utc,delay,ok,(ok?"ELIGIBLE":"LATE_0900_EXIT"));
   }
}

void OnDeinit(const int reason)
{
   if(g_leg!=0 && g_have_last_tick)
   {
      datetime utc=ServerToUtc(g_last_tick.time);
      CloseLeg(g_last_tick,utc,0,false,"TEST_END_FORCE");
   }
   WriteStats("FINAL");
   if(g_trades_fh!=INVALID_HANDLE) FileClose(g_trades_fh);
   if(g_stats_fh!=INVALID_HANDLE) FileClose(g_stats_fh);
}
