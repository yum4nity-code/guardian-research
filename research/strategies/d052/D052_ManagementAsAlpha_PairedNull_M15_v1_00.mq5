#property strict
#property version "1.00"
#property description "D052 Management-as-Alpha paired null-entry lab - exact virtual management on executable ticks"

// D052 preregistration:
// research/campaigns/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_ENTRY_V0_PREREGISTRATION_2026_09_07.md
//
// NO ORDERS. One deterministic price-independent scheduled event per broker day.
// Every event creates simultaneous virtual LONG + SHORT sleeves and evaluates
// the frozen management family on the exact same executable tick stream.

input bool InpWriteCSV=true;

string EXPERIMENT_ID="D052-MANAGEMENT-AS-ALPHA-PAIRED-NULL-ENTRY-V0";
string SOURCE_NAME="D052_ManagementAsAlpha_PairedNull_M15_v1_00.mq5";
string SOURCE_VERSION="1.00";
string RUN_TOKEN="RUN";

#define MGMT_COUNT 12
#define VIRTUAL_COUNT 24

string MGMT_NAMES[MGMT_COUNT]={
   "REF_EOD_NO_STOP",
   "SL1_EOD",
   "SL1_TP1",
   "SL1_TP2",
   "SL1_TP3",
   "SL1_BE_AFTER_1R_EOD",
   "SL1_BE_AFTER_2R_EOD",
   "SL1_P50_AT_1R_BE_REST",
   "SL1_P40_AT_2_5R_BE_REST",
   "SL1_TRAIL1_AFTER_1R",
   "SL1_TRAIL1_5_AFTER_2R",
   "SL1_P50_AT_1R_TRAIL1_REST"
};

struct VTrade
{
   bool active;
   bool long_side;
   int management;
   datetime entry_time;
   long entry_msc;
   datetime broker_day_start;
   int event_day_key;
   int schedule_minute;
   double entry;
   double atr14;
   double risk_money;
   double mfe_r;
   double mae_r;
   bool armed;
   bool partial_done;
   double trail_floor_r;
   double realized_pnl;
   double realized_commission;
   double remaining_fraction;
};

VTrade g_v[VIRTUAL_COUNT];

int g_stats_fh=INVALID_HANDLE;
int g_results_fh=INVALID_HANDLE;
string g_stats_name="";
string g_results_name="";
string g_common_path="";

bool g_have_last_tick=false;
MqlTick g_last_tick;

datetime g_day_start=0;
int g_day_key=0;
int g_schedule_minute=0;
bool g_event_opened=false;
bool g_day_reference_unusable=false;
double g_atr14=0.0;

long g_ticks_seen=0;
long g_days_initialized=0;
long g_reference_unusable_days=0;
long g_schedule_missed_days=0;
long g_paired_events_opened=0;
long g_virtual_opened=0;
long g_virtual_closed=0;
long g_csv_rows=0;
long g_invalid_price=0;
long g_invalid_risk=0;
long g_pnl_calc_failures=0;
string g_fatal_status="";

bool ValidPrice(double x){ return (x>0.0 && MathIsValidNumber(x)); }
long TickMsc(const MqlTick &tick){ return (tick.time_msc>0 ? tick.time_msc : ((long)tick.time)*1000); }
string BoolText(bool x){ return x ? "1" : "0"; }

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
   return (StringFind(_Symbol,"EURUSD")>=0 || StringFind(_Symbol,"GBPUSD")>=0 ||
           StringFind(_Symbol,"USDJPY")>=0 || StringFind(_Symbol,"AUDUSD")>=0 ||
           StringFind(_Symbol,"USDCAD")>=0 || StringFind(_Symbol,"USDCHF")>=0 ||
           StringFind(_Symbol,"SPX500")>=0 || StringFind(_Symbol,"NDX100")>=0 ||
           StringFind(_Symbol,"GER30")>=0 || StringFind(_Symbol,"US30")>=0 ||
           StringFind(_Symbol,"XAUUSD")>=0 || StringFind(_Symbol,"XAGUSD")>=0);
}

string AssetClass()
{
   if(StringFind(_Symbol,"SPX500")>=0 || StringFind(_Symbol,"NDX100")>=0 ||
      StringFind(_Symbol,"GER30")>=0 || StringFind(_Symbol,"US30")>=0) return "INDEX";
   if(StringFind(_Symbol,"XAUUSD")>=0 || StringFind(_Symbol,"XAGUSD")>=0) return "METAL";
   return "FOREX";
}

string CommissionRule()
{
   string c=AssetClass();
   if(c=="FOREX") return "USD5_PER_LOT_PER_SIDE";
   if(c=="METAL") return "0.0016PCT_NOTIONAL_PER_SIDE";
   if(c=="INDEX") return "ZERO_EXPLICIT_COMMISSION";
   return "UNSUPPORTED";
}

void SetFatal(string status,string message)
{
   if(g_fatal_status=="") g_fatal_status=status;
   PrintFormat("D052 V100 FATAL | %s | %s",status,message);
}

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

uint StableScheduleHash(string symbol,int day_key)
{
   uint h=2166136261;
   int n=StringLen(symbol);
   for(int i=0;i<n;i++)
   {
      h^=(uint)StringGetCharacter(symbol,i);
      h*=16777619;
   }
   h^=(uint)day_key;
   h*=16777619;
   h^=(uint)(day_key>>8);
   h*=16777619;
   return h;
}

int ScheduleMinute(string symbol,int day_key)
{
   return 600+(int)(StableScheduleHash(symbol,day_key)%240); // 10:00..13:59 broker time
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

bool CalcMoney1Lot(double entry_px,double exit_px,bool long_side,double &pnl)
{
   if(!ValidPrice(entry_px) || !ValidPrice(exit_px)) return false;
   ENUM_ORDER_TYPE ot=long_side?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   ResetLastError();
   if(!OrderCalcProfit(ot,_Symbol,1.0,entry_px,exit_px,pnl))
   {
      PrintFormat("D052 V100 OrderCalcProfit failed | symbol=%s | err=%d | entry=%.10f | exit=%.10f",_Symbol,GetLastError(),entry_px,exit_px);
      return false;
   }
   return MathIsValidNumber(pnl);
}

bool RiskMoney(double entry_px,double atr,bool long_side,double &risk_money)
{
   if(!(atr>0.0) || !MathIsValidNumber(atr)) return false;
   double adverse=long_side ? entry_px-atr : entry_px+atr;
   if(!ValidPrice(adverse)) return false;
   double pnl=0.0;
   if(!CalcMoney1Lot(entry_px,adverse,long_side,pnl)) return false;
   risk_money=MathAbs(pnl);
   return (risk_money>0.0 && MathIsValidNumber(risk_money));
}

double CommissionRoundTrip1Lot(double entry_px,double exit_px)
{
   if(!ValidPrice(entry_px) || !ValidPrice(exit_px)) return -1.0;
   string c=AssetClass();
   if(c=="FOREX") return 10.0;
   if(c=="INDEX") return 0.0;
   if(c!="METAL") return -1.0;
   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(!(contract>0.0) || !MathIsValidNumber(contract)) return -1.0;
   double rate=0.000016;
   double value=contract*entry_px*rate + contract*exit_px*rate;
   return (value>=0.0 && MathIsValidNumber(value)) ? value : -1.0;
}

bool LoadDayReference(datetime t,const MqlRates &cur)
{
   g_day_start=cur.time;
   g_day_key=DateKey(cur.time);
   g_schedule_minute=ScheduleMinute(_Symbol,g_day_key);
   g_event_opened=false;
   g_day_reference_unusable=false;
   g_atr14=0.0;
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
   if(CopyRates(_Symbol,PERIOD_D1,shift+1,15,refs)!=15)
   {
      g_day_reference_unusable=true;
      g_reference_unusable_days++;
      return true;
   }

   double sum_tr=0.0;
   for(int i=0;i<14;i++)
   {
      if(refs[i].time<=0 || refs[i+1].time<=0 || refs[i].time>=cur.time ||
         !ValidPrice(refs[i].high) || !ValidPrice(refs[i].low) || !ValidPrice(refs[i+1].close) ||
         refs[i].high<=refs[i].low)
      {
         g_day_reference_unusable=true;
         g_reference_unusable_days++;
         return true;
      }
      double tr=MathMax(refs[i].high-refs[i].low,
                        MathMax(MathAbs(refs[i].high-refs[i+1].close),MathAbs(refs[i].low-refs[i+1].close)));
      if(!(tr>0.0) || !MathIsValidNumber(tr))
      {
         g_day_reference_unusable=true;
         g_reference_unusable_days++;
         return true;
      }
      sum_tr+=tr;
   }
   g_atr14=sum_tr/14.0;
   if(!(g_atr14>0.0) || !MathIsValidNumber(g_atr14))
   {
      g_day_reference_unusable=true;
      g_reference_unusable_days++;
   }
   return true;
}

bool AnyActive()
{
   for(int i=0;i<VIRTUAL_COUNT;i++) if(g_v[i].active) return true;
   return false;
}

void ClearVirtual(VTrade &v)
{
   v.active=false;
   v.long_side=false;
   v.management=0;
   v.entry_time=0;
   v.entry_msc=0;
   v.broker_day_start=0;
   v.event_day_key=0;
   v.schedule_minute=0;
   v.entry=0.0;
   v.atr14=0.0;
   v.risk_money=0.0;
   v.mfe_r=0.0;
   v.mae_r=0.0;
   v.armed=false;
   v.partial_done=false;
   v.trail_floor_r=-DBL_MAX;
   v.realized_pnl=0.0;
   v.realized_commission=0.0;
   v.remaining_fraction=1.0;
}

void InitVirtual(VTrade &v,bool long_side,int management,const MqlTick &tick,double entry,double risk_money)
{
   ClearVirtual(v);
   v.active=true;
   v.long_side=long_side;
   v.management=management;
   v.entry_time=tick.time;
   v.entry_msc=TickMsc(tick);
   v.broker_day_start=g_day_start;
   v.event_day_key=g_day_key;
   v.schedule_minute=g_schedule_minute;
   v.entry=entry;
   v.atr14=g_atr14;
   v.risk_money=risk_money;
   v.remaining_fraction=1.0;
}

bool CurrentR(const VTrade &v,double liquidation,double &r,double &pnl1)
{
   if(!CalcMoney1Lot(v.entry,liquidation,v.long_side,pnl1)) return false;
   if(!(v.risk_money>0.0) || !MathIsValidNumber(v.risk_money)) return false;
   r=pnl1/v.risk_money;
   return MathIsValidNumber(r);
}

bool RealizePartial(VTrade &v,double fraction,double liquidation)
{
   if(!(fraction>0.0) || fraction>v.remaining_fraction+1e-12) return false;
   double pnl1=0.0;
   double r=0.0;
   if(!CurrentR(v,liquidation,r,pnl1)) return false;
   double comm=CommissionRoundTrip1Lot(v.entry,liquidation);
   if(comm<0.0 || !MathIsValidNumber(comm)) return false;
   v.realized_pnl+=fraction*pnl1;
   v.realized_commission+=fraction*comm;
   v.remaining_fraction-=fraction;
   if(v.remaining_fraction<1e-12) v.remaining_fraction=0.0;
   v.partial_done=true;
   return true;
}

void WriteStats(string status)
{
   if(g_stats_fh==INVALID_HANDLE) return;
   FileWrite(g_stats_fh,status,SOURCE_NAME,SOURCE_VERSION,RUN_TOKEN,
      g_ticks_seen,g_days_initialized,g_reference_unusable_days,g_schedule_missed_days,
      g_paired_events_opened,g_virtual_opened,g_virtual_closed,g_csv_rows,
      g_invalid_price,g_invalid_risk,g_pnl_calc_failures,g_fatal_status,
      _Symbol,EnumToString(_Period),AssetClass(),CommissionRule(),MGMT_COUNT,
      g_results_name,g_stats_name,g_common_path+g_results_name,g_common_path+g_stats_name);
   FileFlush(g_stats_fh);
}

void CloseVirtual(VTrade &v,const MqlTick &tick,double liquidation,string reason)
{
   if(!v.active) return;
   if(!ValidPrice(liquidation) || !ValidPrice(v.entry) || !(v.risk_money>0.0))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid close inputs");
      v.active=false;
      return;
   }

   double pnl1=0.0;
   double current_r=0.0;
   if(!CurrentR(v,liquidation,current_r,pnl1))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","cannot calculate close PnL");
      v.active=false;
      return;
   }
   double comm1=CommissionRoundTrip1Lot(v.entry,liquidation);
   if(comm1<0.0 || !MathIsValidNumber(comm1))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","cannot calculate close commission");
      v.active=false;
      return;
   }

   double gross_pnl=v.realized_pnl + v.remaining_fraction*pnl1;
   double commission=v.realized_commission + v.remaining_fraction*comm1;
   double gross_r=gross_pnl/v.risk_money;
   double commission_r=commission/v.risk_money;
   double net_r=gross_r-commission_r;
   double stress_r=gross_r-1.5*commission_r;
   if(!MathIsValidNumber(gross_r) || !MathIsValidNumber(commission_r) ||
      !MathIsValidNumber(net_r) || !MathIsValidNumber(stress_r))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","non-finite final R metric");
      v.active=false;
      return;
   }

   double hold_min=((double)(TickMsc(tick)-v.entry_msc))/60000.0;
   string event_id=StringFormat("%s_%d",CleanSymbol(),v.event_day_key);

   if(g_results_fh!=INVALID_HANDLE)
   {
      FileWrite(g_results_fh,
         RUN_TOKEN,_Symbol,AssetClass(),CommissionRule(),event_id,IntegerToString(v.event_day_key),
         TimeToString(v.broker_day_start,TIME_DATE|TIME_MINUTES),v.schedule_minute,
         v.long_side?"LONG":"SHORT",MGMT_NAMES[v.management],
         TimeToString(v.entry_time,TIME_DATE|TIME_SECONDS),TimeToString(tick.time,TIME_DATE|TIME_SECONDS),
         DoubleToString(v.entry,_Digits),DoubleToString(liquidation,_Digits),DoubleToString(v.atr14,_Digits),
         DoubleToString(v.risk_money,8),DoubleToString(gross_r,8),DoubleToString(commission_r,8),
         DoubleToString(net_r,8),DoubleToString(stress_r,8),reason,
         BoolText(v.partial_done),DoubleToString(v.mfe_r,8),DoubleToString(v.mae_r,8),DoubleToString(hold_min,6));
      FileFlush(g_results_fh);
      g_csv_rows++;
   }

   v.remaining_fraction=0.0;
   v.active=false;
   g_virtual_closed++;
}

void ProcessVirtual(VTrade &v,const MqlTick &tick)
{
   if(!v.active || g_fatal_status!="") return;
   double liquidation=v.long_side ? tick.bid : tick.ask;
   if(!ValidPrice(liquidation))
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid executable liquidation tick");
      return;
   }

   double r=0.0;
   double pnl1=0.0;
   if(!CurrentR(v,liquidation,r,pnl1))
   {
      g_pnl_calc_failures++;
      SetFatal("FINAL_INVALID_PNL_CALC","cannot calculate path R");
      return;
   }
   if(r>v.mfe_r) v.mfe_r=r;
   if(-r>v.mae_r) v.mae_r=-r;

   int m=v.management;
   if(m==0) return; // reference: EOD only, no active management

   // All active candidates have the same hard initial -1R stop.
   if(r<=-1.0)
   {
      CloseVirtual(v,tick,liquidation,"SL1");
      return;
   }

   if(m==1) return; // SL1_EOD

   if(m==2 && r>=1.0){ CloseVirtual(v,tick,liquidation,"TP1"); return; }
   if(m==3 && r>=2.0){ CloseVirtual(v,tick,liquidation,"TP2"); return; }
   if(m==4 && r>=3.0){ CloseVirtual(v,tick,liquidation,"TP3"); return; }

   if(m==5)
   {
      if(!v.armed && r>=1.0) v.armed=true;
      if(v.armed && r<=0.0){ CloseVirtual(v,tick,liquidation,"BE_AFTER_1R"); return; }
      return;
   }

   if(m==6)
   {
      if(!v.armed && r>=2.0) v.armed=true;
      if(v.armed && r<=0.0){ CloseVirtual(v,tick,liquidation,"BE_AFTER_2R"); return; }
      return;
   }

   if(m==7)
   {
      if(!v.partial_done && r>=1.0)
      {
         if(!RealizePartial(v,0.50,liquidation))
         {
            g_pnl_calc_failures++;
            SetFatal("FINAL_INVALID_PNL_CALC","P50 partial realization failed");
            return;
         }
         v.armed=true;
      }
      if(v.partial_done && r<=0.0){ CloseVirtual(v,tick,liquidation,"P50_1R_BE_REST"); return; }
      return;
   }

   if(m==8)
   {
      if(!v.partial_done && r>=2.5)
      {
         if(!RealizePartial(v,0.40,liquidation))
         {
            g_pnl_calc_failures++;
            SetFatal("FINAL_INVALID_PNL_CALC","P40 partial realization failed");
            return;
         }
         v.armed=true;
      }
      if(v.partial_done && r<=0.0){ CloseVirtual(v,tick,liquidation,"P40_2_5R_BE_REST"); return; }
      return;
   }

   if(m==9)
   {
      if(!v.armed && r>=1.0) v.armed=true;
      if(v.armed)
      {
         double floor_r=v.mfe_r-1.0;
         if(floor_r>v.trail_floor_r) v.trail_floor_r=floor_r;
         if(r<=v.trail_floor_r){ CloseVirtual(v,tick,liquidation,"TRAIL1_AFTER_1R"); return; }
      }
      return;
   }

   if(m==10)
   {
      if(!v.armed && r>=2.0) v.armed=true;
      if(v.armed)
      {
         double floor_r=v.mfe_r-1.5;
         if(floor_r>v.trail_floor_r) v.trail_floor_r=floor_r;
         if(r<=v.trail_floor_r){ CloseVirtual(v,tick,liquidation,"TRAIL1_5_AFTER_2R"); return; }
      }
      return;
   }

   if(m==11)
   {
      if(!v.partial_done && r>=1.0)
      {
         if(!RealizePartial(v,0.50,liquidation))
         {
            g_pnl_calc_failures++;
            SetFatal("FINAL_INVALID_PNL_CALC","P50 trail partial realization failed");
            return;
         }
         v.armed=true;
      }
      if(v.partial_done)
      {
         double floor_r=v.mfe_r-1.0;
         if(floor_r>v.trail_floor_r) v.trail_floor_r=floor_r;
         if(r<=v.trail_floor_r){ CloseVirtual(v,tick,liquidation,"P50_1R_TRAIL1_REST"); return; }
      }
      return;
   }
}

void ProcessAll(const MqlTick &tick)
{
   for(int i=0;i<VIRTUAL_COUNT;i++)
   {
      if(g_fatal_status!="") return;
      ProcessVirtual(g_v[i],tick);
   }
}

void CloseAll(const MqlTick &tick,string reason)
{
   for(int i=0;i<VIRTUAL_COUNT;i++)
   {
      if(!g_v[i].active) continue;
      double liquidation=g_v[i].long_side ? tick.bid : tick.ask;
      CloseVirtual(g_v[i],tick,liquidation,reason);
      if(g_fatal_status!="") return;
   }
}

bool OpenPairedEvent(const MqlTick &tick)
{
   if(g_event_opened || g_day_reference_unusable || !(g_atr14>0.0)) return false;
   double long_entry=tick.ask;
   double short_entry=tick.bid;
   if(!ValidPrice(long_entry) || !ValidPrice(short_entry) || long_entry<short_entry)
   {
      g_invalid_price++;
      SetFatal("FINAL_INVALID_PRICE","invalid paired entry bid/ask");
      return false;
   }

   double long_risk=0.0;
   double short_risk=0.0;
   if(!RiskMoney(long_entry,g_atr14,true,long_risk) || !RiskMoney(short_entry,g_atr14,false,short_risk))
   {
      g_invalid_risk++;
      SetFatal("FINAL_INVALID_RISK","cannot calculate paired 1ATR risk money");
      return false;
   }

   int idx=0;
   for(int side=0;side<2;side++)
   {
      bool long_side=(side==0);
      double entry=long_side ? long_entry : short_entry;
      double risk=long_side ? long_risk : short_risk;
      for(int m=0;m<MGMT_COUNT;m++)
      {
         InitVirtual(g_v[idx],long_side,m,tick,entry,risk);
         idx++;
         g_virtual_opened++;
      }
   }
   g_event_opened=true;
   g_paired_events_opened++;
   return true;
}

int OnInit()
{
   if(_Period!=PERIOD_M15)
   {
      PrintFormat("D052 V100 FATAL wrong timeframe | got=%s",EnumToString(_Period));
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!InpWriteCSV)
   {
      Print("D052 V100 FATAL InpWriteCSV must remain true");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!IsAllowedSymbol())
   {
      PrintFormat("D052 V100 FATAL symbol outside frozen universe | %s",_Symbol);
      return INIT_PARAMETERS_INCORRECT;
   }
   if(AccountInfoString(ACCOUNT_CURRENCY)!="USD")
   {
      PrintFormat("D052 V100 FATAL USD account required | got=%s",AccountInfoString(ACCOUNT_CURRENCY));
      return INIT_PARAMETERS_INCORRECT;
   }

   for(int i=0;i<VIRTUAL_COUNT;i++) ClearVirtual(g_v[i]);

   string sym=CleanSymbol();
   g_stats_name=StringFormat("D052_V100_RUN_%s_STATS.csv",sym);
   g_results_name=StringFormat("D052_V100_RUN_%s_RESULTS.csv",sym);
   g_common_path=TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";

   g_stats_fh=FileOpen(g_stats_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_stats_fh==INVALID_HANDLE)
   {
      PrintFormat("D052 V100 FATAL cannot open STATS | err=%d",GetLastError());
      return INIT_FAILED;
   }
   FileWrite(g_stats_fh,
      "status","source_name","source_version","run_stage","ticks_seen","days_initialized","reference_unusable_days",
      "schedule_missed_days","paired_events_opened","virtual_opened","virtual_closed","csv_rows","invalid_price",
      "invalid_risk","pnl_calc_failures","fatal_status","symbol","timeframe","asset_class","commission_rule",
      "management_count","results_name","stats_name","results_csv_fullpath","stats_csv_fullpath");
   WriteStats("INIT");

   g_results_fh=FileOpen(g_results_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_results_fh==INVALID_HANDLE)
   {
      SetFatal("FINAL_RESULTS_OPEN_FAILED","cannot open RESULTS CSV");
      WriteStats("FINAL");
      FileClose(g_stats_fh); g_stats_fh=INVALID_HANDLE;
      return INIT_FAILED;
   }
   FileWrite(g_results_fh,
      "run_stage","symbol","asset_class","commission_rule","event_id","day_key","broker_day_start","schedule_minute",
      "side","management","entry_time","exit_time","entry","exit","atr14","risk_money_1lot_usd","gross_r",
      "commission_r","net_r","net_r_commission_x1_5","exit_reason","partial_triggered","mfe_r","mae_r","holding_minutes");
   FileFlush(g_results_fh);
   WriteStats("READY");

   PrintFormat("D052 V100 READY | source=%s | symbol=%s | paired null entries | %d managements | Model0 required | NO ORDERS",
               SOURCE_NAME,_Symbol,MGMT_COUNT);
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
      SetFatal("FINAL_INVALID_PRICE","cannot resolve current D1 bar");
      return;
   }

   if(g_day_start==0 || cur.time!=g_day_start)
   {
      if(g_day_start!=0)
      {
         if(AnyActive())
         {
            if(!g_have_last_tick)
            {
               SetFatal("FINAL_INVALID_LIFECYCLE","day changed with active virtual trades and no last tick");
               return;
            }
            CloseAll(g_last_tick,"EOD");
            if(g_fatal_status!="") return;
         }
         if(!g_event_opened && !g_day_reference_unusable) g_schedule_missed_days++;
      }
      if(!LoadDayReference(tick.time,cur)) return;
   }

   int minute=MinuteOfDay(tick.time);
   if(!g_event_opened && !g_day_reference_unusable && minute>=g_schedule_minute && minute<=900)
   {
      if(OpenPairedEvent(tick))
      {
         ProcessAll(tick);
         if(g_fatal_status!="") return;
      }
   }
   else if(AnyActive())
   {
      ProcessAll(tick);
      if(g_fatal_status!="") return;
   }

   g_last_tick=tick;
   g_have_last_tick=true;
}

void OnDeinit(const int reason)
{
   if(g_fatal_status=="" && AnyActive())
   {
      if(g_have_last_tick) CloseAll(g_last_tick,"TEST_END");
      else SetFatal("FINAL_INVALID_LIFECYCLE","tester ended with active virtual trades and no last tick");
   }
   if(g_stats_fh!=INVALID_HANDLE) WriteStats("FINAL");
   if(g_results_fh!=INVALID_HANDLE){ FileFlush(g_results_fh); FileClose(g_results_fh); g_results_fh=INVALID_HANDLE; }
   if(g_stats_fh!=INVALID_HANDLE){ FileFlush(g_stats_fh); FileClose(g_stats_fh); g_stats_fh=INVALID_HANDLE; }
}
