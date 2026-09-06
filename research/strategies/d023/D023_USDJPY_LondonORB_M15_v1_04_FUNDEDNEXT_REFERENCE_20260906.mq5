#property strict
#property version "1.04"
#property description "D023 USDJPY London ORB M15 - FundedNext clock/cost conformance - no orders"

// D023 frozen London ORB V0.
// NO strategy tuning here.
// Changes vs v1.02 are conformance only:
//   - FundedNext server clock (GMT+2 / GMT+3 with US DST schedule)
//   - Europe/London DST-aware conversion
//   - FundedNext Forex commission written in R
//   - isolated CSV filename (no accumulation with old D023 files)
//
// FIRST CONTROL RUN:
//   USDJPY, M15, Every tick
//   2024.01.02 -> 2026.06.26
//
// IMPORTANT:
//   Do NOT use 2023 yet. It remains reserved as confirmation data.

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
datetime g_last_closed=0;
string g_day="";
double g_or_hi=0.0,g_or_lo=0.0,g_entry=0.0,g_sl=0.0,g_risk=0.0;
int g_or_count=0;
bool g_signalled=false,g_in_trade=false,g_is_long=false;
datetime g_entry_time=0;

bool IsLeap(int y){return ((y%4)==0 && ((y%100)!=0 || (y%400)==0));}
int DaysInMonth(int y,int m){if(m==2)return IsLeap(y)?29:28;if(m==4||m==6||m==9||m==11)return 30;return 31;}
datetime MakeDT(int y,int m,int d,int hh=0,int mm=0,int ss=0){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=hh;x.min=mm;x.sec=ss;return StructToTime(x);}
int WeekdayOfDate(int y,int m,int d){MqlDateTime x;TimeToStruct(MakeDT(y,m,d,12,0,0),x);return x.day_of_week;}
int NthSunday(int y,int m,int nth){int first_wd=WeekdayOfDate(y,m,1);int first_sunday=1+((7-first_wd)%7);return first_sunday+7*(nth-1);}
int LastSunday(int y,int m){int last=DaysInMonth(y,m);int wd=WeekdayOfDate(y,m,last);return last-wd;}

int FundedNextServerUTCOffsetHours(datetime server_t)
{
   MqlDateTime s;TimeToStruct(server_t,s);int y=s.year;
   int us_start=NthSunday(y,3,2),us_end=NthSunday(y,11,1);bool dst=false;
   if(s.mon>3&&s.mon<11)dst=true;else if(s.mon==3&&s.day>=us_start)dst=true;else if(s.mon==11&&s.day<us_end)dst=true;
   return dst?3:2;
}

int LondonUTCOffsetHours(datetime server_t)
{
   MqlDateTime s;TimeToStruct(server_t,s);int y=s.year;
   int uk_start=LastSunday(y,3),uk_end=LastSunday(y,10);bool dst=false;
   if(s.mon>3&&s.mon<10)dst=true;else if(s.mon==3&&s.day>=uk_start)dst=true;else if(s.mon==10&&s.day<uk_end)dst=true;
   return dst?1:0;
}

datetime LondonTime(datetime server_t){int diff=FundedNextServerUTCOffsetHours(server_t)-LondonUTCOffsetHours(server_t);return server_t-diff*3600;}
int LMin(datetime server_t){MqlDateTime d;TimeToStruct(LondonTime(server_t),d);return d.hour*60+d.min;}
int LWeekday(datetime server_t){MqlDateTime d;TimeToStruct(LondonTime(server_t),d);return d.day_of_week;}
string LDay(datetime server_t){MqlDateTime d;TimeToStruct(LondonTime(server_t),d);return StringFormat("%04d-%02d-%02d",d.year,d.mon,d.day);}

double ForexCommissionPerLotSideUSD(){if(InpFundedNextModel==FN_STELLAR_1STEP_2STEP)return 5.00;if(InpFundedNextModel==FN_STELLAR_LITE)return 7.00;if(InpFundedNextModel==FN_STELLAR_INSTANT)return 7.00;return MathMax(0.0,InpCustomForexCommissionUSDPerLotSide);}
string CommissionModelName(){if(InpFundedNextModel==FN_STELLAR_1STEP_2STEP)return "STELLAR_1STEP_2STEP";if(InpFundedNextModel==FN_STELLAR_LITE)return "STELLAR_LITE";if(InpFundedNextModel==FN_STELLAR_INSTANT)return "STELLAR_INSTANT";return "CUSTOM_PER_SIDE";}

double Spr(const MqlRates &b){return (double)b.spread*_Point;}
double EntryPx(bool long_side,const MqlRates &cur){return long_side?cur.open+Spr(cur):cur.open;}
double ExitPx(bool long_side,const MqlRates &b){return long_side?b.close:b.close+Spr(b);}
bool StopHit(bool long_side,const MqlRates &b,double stop_px){return long_side?b.low<=stop_px:b.high+Spr(b)>=stop_px;}

double CommissionR()
{
   if(g_risk<=0.0||g_entry<=0.0||g_sl<=0.0)return -1.0;
   double risk_money=0.0;ENUM_ORDER_TYPE ot=g_is_long?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(ot,_Symbol,1.0,g_entry,g_sl,risk_money))return -1.0;
   risk_money=MathAbs(risk_money);if(risk_money<=0.0)return -1.0;
   return 2.0*ForexCommissionPerLotSideUSD()/risk_money;
}

void ResetDay(string d){g_day=d;g_or_hi=0.0;g_or_lo=0.0;g_or_count=0;g_signalled=false;g_in_trade=false;g_entry=0.0;g_sl=0.0;g_risk=0.0;g_entry_time=0;}

void WriteTrade(datetime xt,double xp,string why)
{
   double pnl=g_is_long?xp-g_entry:g_entry-xp;double gross_r=(g_risk>0.0?pnl/g_risk:0.0);double commission_r=CommissionR();double net_r=(commission_r>=0.0?gross_r-commission_r:gross_r);
   if(g_fh!=INVALID_HANDLE)
   {
      FileWrite(g_fh,g_day,_Symbol,CommissionModelName(),DoubleToString(ForexCommissionPerLotSideUSD(),2),g_is_long?"LONG":"SHORT",TimeToString(g_entry_time,TIME_DATE|TIME_MINUTES),TimeToString(xt,TIME_DATE|TIME_MINUTES),TimeToString(LondonTime(g_entry_time),TIME_DATE|TIME_MINUTES),TimeToString(LondonTime(xt),TIME_DATE|TIME_MINUTES),IntegerToString(FundedNextServerUTCOffsetHours(g_entry_time)),IntegerToString(LondonUTCOffsetHours(g_entry_time)),DoubleToString(g_or_hi,_Digits),DoubleToString(g_or_lo,_Digits),DoubleToString(g_entry,_Digits),DoubleToString(g_sl,_Digits),DoubleToString(xp,_Digits),DoubleToString(g_risk,_Digits),DoubleToString(gross_r,8),DoubleToString(commission_r,8),DoubleToString(net_r,8),why);
      FileFlush(g_fh);
   }
   g_in_trade=false;
}

int OnInit()
{
   if(InpRequireUSDJPY&&StringFind(_Symbol,"USDJPY")<0){Print("D023 v1.04 FundedNext: USDJPY only.");return INIT_PARAMETERS_INCORRECT;}
   if(_Period!=PERIOD_M15)Print("D023 v1.04 FundedNext: use M15 in Strategy Tester.");
   if(InpWriteCSV)
   {
      string p="D023_USDJPY_ORB_V104_FUNDEDNEXT_CONFORMANCE.csv";
      g_fh=FileOpen(p,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
      if(g_fh==INVALID_HANDLE){PrintFormat("D023 v1.04: FileOpen failed err=%d",GetLastError());return INIT_FAILED;}
      FileWrite(g_fh,"london_day","symbol","fundednext_model","commission_usd_per_lot_side","side","entry_time_server","exit_time_server","entry_time_london","exit_time_london","server_utc_offset_h","london_utc_offset_h","or_high","or_low","entry","stop","exit","risk_price","gross_r","commission_r","net_r","exit_reason");
   }
   PrintFormat("D023 USDJPY ORB v1.04 FUNDEDNEXT | NO ORDERS | model=%s | FX commission %.2f USD/lot/side",CommissionModelName(),ForexCommissionPerLotSideUSD());
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){if(g_fh!=INVALID_HANDLE)FileClose(g_fh);}

void OnTick()
{
   MqlRates r[];ArrayResize(r,2);ArraySetAsSeries(r,true);if(CopyRates(_Symbol,PERIOD_M15,0,2,r)!=2)return;MqlRates cur=r[0],b=r[1];if(b.time==g_last_closed)return;g_last_closed=b.time;
   string d=LDay(b.time);if(g_day=="")ResetDay(d);if(d!=g_day)ResetDay(d);int wd=LWeekday(b.time);if(wd==0||wd==6)return;int m=LMin(b.time);
   if(m>=480&&m<540){if(g_or_count==0){g_or_hi=b.high;g_or_lo=b.low;}else{if(b.high>g_or_hi)g_or_hi=b.high;if(b.low<g_or_lo)g_or_lo=b.low;}g_or_count++;}
   if(g_in_trade){if(StopHit(g_is_long,b,g_sl)){WriteTrade(b.time,g_sl,"STOP");return;}if(m==945){WriteTrade(b.time,ExitPx(g_is_long,b),"TIME_1600");return;}}
   if(!g_in_trade&&!g_signalled&&g_or_count==4&&m>=540&&m<660){bool lg=b.close>g_or_hi,sh=b.close<g_or_lo;if(lg||sh){g_signalled=true;g_is_long=lg;g_entry=EntryPx(g_is_long,cur);g_sl=g_is_long?g_or_lo:g_or_hi;g_risk=g_is_long?g_entry-g_sl:g_sl-g_entry;if(g_risk>0.0){g_in_trade=true;g_entry_time=cur.time;}}}
}
