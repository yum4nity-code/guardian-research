#property strict
#property version   "1.01"
#property description "RSI Sniper v11.16.11 entry-path diagnostic 1.01 - legacy closed-bar recross, no orders"

// Extracted from Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.
// This observer targets the RSI version that produced the earlier spectacular backtests.
// Preserved signal mechanics: RSI(14) M1 oversold episode <30, closed-bar recross >30,
// BUY1 structural stop = episode low - 0.15 ATR(14) M1, legacy spread/SL <=25% with BUY1 auto-widen <=1 ATR,
// optional BUY2 on a second oversold episode before RSI50 with RSI bullish divergence and low retest <= first low +0.50 ATR.
// It records each virtual leg independently for first-touch R diagnostics and RSI50/RSI70 timing.
// This is explicitly an ENTRY-PATH diagnostic, not an exact emulation of the production runner lifecycle.
// Excluded deliberately: account drawdown/position caps/news/cooldown-after-losses/min-lot/margin/actual order fills.
// Production concurrency after TP1 is NOT reproduced: once RSI50 is observed the sensing cycle is retired so the entry edge can be tested independently.

input int  InpMaxHoldHours = 48;
input bool InpVerbose = false;
input bool InpUseProductionSessionGate = true;

#define RSI_PERIOD 14
#define ATR_PERIOD 14
#define OVERSOLD 30.0
#define RESET_RSI 40.0
#define TP1_RSI 50.0
#define TP2_RSI 70.0
#define SL_BUFFER_ATR 0.15
#define MAX_SPREAD_PCT_SL 25.0
#define MAX_SL_WIDEN_ATR 1.00
#define BUY2_RETEST_ATR 0.50
#define MAX_TRACKED 1024
#define CLASSIC_SESSION_START 7.0
#define CLASSIC_SESSION_END 17.0

enum RState { RS_IDLE=0, RS_ARMED1, RS_ACTIVE, RS_ARMED2, RS_COOLDOWN };

struct VTrade
{
   bool active;
   string event_id;
   int leg;
   datetime entry_time;
   double entry,stop,risk;
   double mfe_r,mae_r;
   datetime hit05,hit1,hit125,hit15,hit2,hit25,hit3,hit4,hit5;
   datetime stop_time,be1_time,be125_time,rsi50_time,rsi70_time;
   bool amb_stop_target,amb_be1,amb_be125;
   bool h1,h4,h8,h24,h48;
};

int g_rsi=INVALID_HANDLE,g_atr=INVALID_HANDLE;
datetime g_last_m1_open=0;
string g_session="";
long g_event_counter=0,g_cycle_counter=0;
RState g_state=RS_IDLE;
bool g_cycle_active=false,g_tp1_seen=false;
int g_legs=0;
datetime g_cycle_start=0;
double g_episode_min=1000.0,g_episode_low=1e100;
double g_first_min=1000.0,g_first_low=0.0,g_first_stop=0.0;
double g_second_min=1000.0,g_second_low=1e100;
double g_common_stop=0.0;
VTrade g_trades[MAX_TRACKED];

bool IsCrypto()
{
   string u=_Symbol;StringToUpper(u);
   return (StringFind(u,"BTC")>=0||StringFind(u,"ETH")>=0||StringFind(u,"SOL")>=0||StringFind(u,"XRP")>=0||StringFind(u,"DOG")>=0||StringFind(u,"ADA")>=0||StringFind(u,"LNK")>=0||StringFind(u,"LINK")>=0||StringFind(u,"LTC")>=0||StringFind(u,"BCH")>=0||StringFind(u,"DOT")>=0||StringFind(u,"AVAX")>=0||StringFind(u,"XMR")>=0||StringFind(u,"ETC")>=0);
}

bool AllowedSession(datetime t)
{
   if(!InpUseProductionSessionGate||IsCrypto())return true;
   MqlDateTime d;TimeToStruct(t,d);if(d.day_of_week==0||d.day_of_week==6)return false;double h=d.hour+d.min/60.0;if(d.day_of_week==5&&h>=20.0)return false;return(h>=CLASSIC_SESSION_START&&h<CLASSIC_SESSION_END);
}

void EnsureFolder(){FolderCreate("GuardianResearch",FILE_COMMON);FolderCreate("GuardianResearch\\RSILegacy111611",FILE_COMMON);}
string EventsFile(){return "GuardianResearch\\RSILegacy111611\\rsi_111611_virtual_events.csv";}
string TradesFile(){return "GuardianResearch\\RSILegacy111611\\rsi_111611_virtual_trades.csv";}
string OutcomesFile(){return "GuardianResearch\\RSILegacy111611\\rsi_111611_virtual_outcomes.csv";}

void LogEvent(string event_id,string transition,int leg,datetime t,double rsi,double atr,double price,double stop,string context)
{
   EnsureFolder();int h=FileOpen(EventsFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0)FileWrite(h,"session_id","event_id","time","symbol","strategy","variant","cycle_id","leg","transition","rsi","atr_m1","price","stop","context");
   FileSeek(h,0,SEEK_END);FileWrite(h,g_session,event_id,TimeToString(t,TIME_DATE|TIME_SECONDS),_Symbol,"RSI_SNIPER","V11_16_11_CLOSED_BAR",g_cycle_counter,leg,transition,DoubleToString(rsi,4),DoubleToString(atr,8),DoubleToString(price,_Digits),DoubleToString(stop,_Digits),context);FileClose(h);
}

void LogTrade(VTrade &v,string context)
{
   EnsureFolder();int h=FileOpen(TradesFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0)FileWrite(h,"session_id","event_id","entry_utc","symbol","strategy","variant","side","leg","entry","sl","risk_price","signal_tf","context");
   FileSeek(h,0,SEEK_END);FileWrite(h,g_session,v.event_id,TimeToString(v.entry_time,TIME_DATE|TIME_SECONDS),_Symbol,"RSI_SNIPER","V11_16_11_CLOSED_BAR","BUY",v.leg,DoubleToString(v.entry,_Digits),DoubleToString(v.stop,_Digits),DoubleToString(v.risk,_Digits),"PERIOD_M1",context);FileClose(h);
}

void LogOutcome(VTrade &v,string horizon,datetime t)
{
   EnsureFolder();int h=FileOpen(OutcomesFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0)FileWrite(h,"session_id","event_id","utc_text","symbol","strategy","side","leg","horizon","mfe_r","mae_r","hit05_utc","hit1_utc","hit125_utc","hit15_utc","hit2_utc","hit25_utc","hit3_utc","hit4_utc","hit5_utc","stop_utc","be_after1_utc","be_after125_utc","rsi50_utc","rsi70_utc","ambiguous_stop_target_m1","ambiguous_be1_m1","ambiguous_be125_m1");
   FileSeek(h,0,SEEK_END);FileWrite(h,g_session,v.event_id,TimeToString(t,TIME_DATE|TIME_SECONDS),_Symbol,"RSI_SNIPER","BUY",v.leg,horizon,DoubleToString(v.mfe_r,6),DoubleToString(v.mae_r,6),(long)v.hit05,(long)v.hit1,(long)v.hit125,(long)v.hit15,(long)v.hit2,(long)v.hit25,(long)v.hit3,(long)v.hit4,(long)v.hit5,(long)v.stop_time,(long)v.be1_time,(long)v.be125_time,(long)v.rsi50_time,(long)v.rsi70_time,(v.amb_stop_target?"YES":"NO"),(v.amb_be1?"YES":"NO"),(v.amb_be125?"YES":"NO"));FileClose(h);
}

double Buf(int h,int shift){double x[1];if(h==INVALID_HANDLE||CopyBuffer(h,0,shift,1,x)!=1)return EMPTY_VALUE;return x[0];}
int FreeSlot(){for(int i=0;i<MAX_TRACKED;i++)if(!g_trades[i].active)return i;return -1;}

void SetHit(VTrade &v,double r,datetime t)
{
   if(r==0.5&&v.hit05==0)v.hit05=t;else if(r==1&&v.hit1==0)v.hit1=t;else if(r==1.25&&v.hit125==0)v.hit125=t;else if(r==1.5&&v.hit15==0)v.hit15=t;else if(r==2&&v.hit2==0)v.hit2=t;else if(r==2.5&&v.hit25==0)v.hit25=t;else if(r==3&&v.hit3==0)v.hit3=t;else if(r==4&&v.hit4==0)v.hit4=t;else if(r==5&&v.hit5==0)v.hit5=t;
}
datetime GetHit(VTrade &v,double r){if(r==0.5)return v.hit05;if(r==1)return v.hit1;if(r==1.25)return v.hit125;if(r==1.5)return v.hit15;if(r==2)return v.hit2;if(r==2.5)return v.hit25;if(r==3)return v.hit3;if(r==4)return v.hit4;if(r==5)return v.hit5;return 0;}

void MarkRSILevels(double rsi,datetime t)
{
   for(int i=0;i<MAX_TRACKED;i++)if(g_trades[i].active)
   {
      if(g_trades[i].rsi50_time==0&&rsi>=TP1_RSI)g_trades[i].rsi50_time=t;
      if(g_trades[i].rsi70_time==0&&rsi>=TP2_RSI)g_trades[i].rsi70_time=t;
   }
}

void ProcessPath(VTrade &v,MqlRates &b,datetime t)
{
   datetime bc=b.time+60;if(bc<=v.entry_time||v.risk<=0)return;
   double fav=MathMax(0.0,b.high-v.entry)/v.risk,adv=MathMax(0.0,v.entry-b.low)/v.risk;v.mfe_r=MathMax(v.mfe_r,fav);v.mae_r=MathMax(v.mae_r,adv);
   bool stop_cross=(v.stop_time==0&&b.low<=v.stop),new_target=false;double rr[9]={0.5,1.0,1.25,1.5,2.0,2.5,3.0,4.0,5.0};
   for(int j=0;j<9;j++)if(GetHit(v,rr[j])==0){double px=v.entry+rr[j]*v.risk;if(b.high>=px){SetHit(v,rr[j],t);new_target=true;}}
   bool h1this=(v.hit1==t),h125this=(v.hit125==t);
   if(v.be1_time==0&&v.hit1>0&&b.low<=v.entry){v.be1_time=t;if(h1this)v.amb_be1=true;}
   if(v.be125_time==0&&v.hit125>0&&b.low<=v.entry){v.be125_time=t;if(h125this)v.amb_be125=true;}
   if(stop_cross){v.stop_time=t;if(new_target)v.amb_stop_target=true;}
   long e=(long)(t-v.entry_time);if(!v.h1&&e>=3600){v.h1=true;LogOutcome(v,"1H",t);}if(!v.h4&&e>=14400){v.h4=true;LogOutcome(v,"4H",t);}if(!v.h8&&e>=28800){v.h8=true;LogOutcome(v,"8H",t);}if(!v.h24&&e>=86400){v.h24=true;LogOutcome(v,"24H",t);}if(!v.h48&&e>=InpMaxHoldHours*3600){v.h48=true;LogOutcome(v,StringFormat("%dH",InpMaxHoldHours),t);v.active=false;}
}

void RetireCycle(string why,double rsi,double atr,datetime t)
{
   if(g_cycle_active)LogEvent(StringFormat("RSICYCLE_%I64d",g_cycle_counter),"CYCLE_RETIRED",0,t,rsi,atr,0,g_common_stop,why);
   g_cycle_active=false;g_tp1_seen=false;g_legs=0;g_cycle_start=0;g_episode_min=1000;g_episode_low=1e100;g_first_min=1000;g_first_low=0;g_first_stop=0;g_second_min=1000;g_second_low=1e100;g_common_stop=0;g_state=RS_COOLDOWN;
}

bool PrepareVirtualEntry(int leg,double desired_stop,double atr,double rsi,double &entry,double &final_stop,string &reject)
{
   reject="";MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0||q.ask<=q.bid){reject="INVALID_TICK";return false;}if(!AllowedSession(TimeCurrent())){reject="SESSION";return false;}
   final_stop=NormalizeDouble(desired_stop,_Digits);if(final_stop<=0||final_stop>=q.bid){reject="INVALID_STOP";return false;}
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);int stops_level=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(point<=0.0 || q.bid-final_stop<stops_level*point){reject="INVALID_BROKER_STOP";return false;}
   entry=q.ask;double dist=entry-final_stop;if(dist<=0){reject="INVALID_DISTANCE";return false;}
   double spread=q.ask-q.bid,pct=100.0*spread/dist;
   if(pct>MAX_SPREAD_PCT_SL)
   {
      bool adapted=false;if(leg==1&&atr>0)
      {
         double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);double req=spread*100.0/MAX_SPREAD_PCT_SL+tick;double extra=req-dist;
         if(extra>=0&&extra<=MAX_SL_WIDEN_ATR*atr+tick){double candidate=NormalizeDouble(q.ask-req,_Digits);if(candidate>0&&candidate<q.bid && q.bid-candidate>=stops_level*point){final_stop=candidate;dist=entry-final_stop;pct=100.0*spread/dist;adapted=(pct<=MAX_SPREAD_PCT_SL+0.10);}}
      }
      if(!adapted){reject="SPREAD";return false;}
   }
   return true;
}

bool CreateLeg(int leg,double desired_stop,double atr,double rsi,string context)
{
   double entry=0,stop=0;string rej="";string eid=StringFormat("RSI111611_%s_C%I64d_L%d_%I64d",_Symbol,g_cycle_counter,leg,++g_event_counter);
   if(!PrepareVirtualEntry(leg,desired_stop,atr,rsi,entry,stop,rej)){LogEvent(eid,"REJECT_"+rej,leg,TimeCurrent(),rsi,atr,entry,stop,context);return false;}
   int s=FreeSlot();if(s<0){LogEvent(eid,"REJECT_NO_SLOT",leg,TimeCurrent(),rsi,atr,entry,stop,context);return false;}
   VTrade v;ZeroMemory(v);v.active=true;v.event_id=eid;v.leg=leg;v.entry_time=TimeCurrent();v.entry=entry;v.stop=stop;v.risk=entry-stop;if(v.risk<=0){LogEvent(eid,"REJECT_BAD_RISK",leg,TimeCurrent(),rsi,atr,entry,stop,context);return false;}
   g_trades[s]=v;LogEvent(eid,"VALID_SIGNAL",leg,v.entry_time,rsi,atr,entry,stop,context);LogTrade(g_trades[s],context);
   if(InpVerbose)Print("[RSI111611] ",eid," BUY",leg," entry=",DoubleToString(entry,_Digits)," SL=",DoubleToString(stop,_Digits));
   if(leg==1){g_first_stop=stop;g_common_stop=stop;}else g_common_stop=MathMax(g_common_stop,stop);
   return true;
}

void ProcessRSIState(MqlRates &b,double r1,double r2,double atr,datetime t)
{
   MarkRSILevels(r1,t);
   if(g_cycle_active && g_cycle_start>0 && (t-g_cycle_start)>=InpMaxHoldHours*3600){RetireCycle("SENSING_TIMEOUT",r1,atr,t);return;}

   if(g_cycle_active)
   {
      if(b.low<=g_common_stop){RetireCycle("COMMON_STOP_TOUCHED",r1,atr,t);return;}
      if(!g_tp1_seen && r1>=TP1_RSI){g_tp1_seen=true;LogEvent(StringFormat("RSICYCLE_%I64d",g_cycle_counter),"RSI50_TP1_TRIGGER",0,t,r1,atr,b.close,g_common_stop,"legacy TP1 sensing terminal");RetireCycle("RSI50_REACHED",r1,atr,t);return;}
      if(g_legs==1)
      {
         if(g_state==RS_ACTIVE && r2>=OVERSOLD && r1<OVERSOLD){g_state=RS_ARMED2;g_second_min=r1;g_second_low=b.low;LogEvent(StringFormat("RSICYCLE_%I64d",g_cycle_counter),"ARM_BUY2",2,t,r1,atr,b.close,g_common_stop,"");return;}
         if(g_state==RS_ARMED2)
         {
            g_second_min=MathMin(g_second_min,r1);g_second_low=MathMin(g_second_low,b.low);
            if(r2<=OVERSOLD && r1>OVERSOLD)
            {
               bool divergence=(g_second_min>g_first_min);bool retest=(g_second_low<=g_first_low+BUY2_RETEST_ATR*atr);
               if(divergence&&retest)
               {
                  double structural=g_second_low-SL_BUFFER_ATR*atr;double common=MathMax(g_common_stop,structural);
                  if(CreateLeg(2,common,atr,r1,StringFormat("div=%.2f|lowgap=%.3fATR",g_second_min-g_first_min,(g_second_low-g_first_low)/atr))){g_legs=2;g_common_stop=MathMax(g_common_stop,common);}
               }
               else LogEvent(StringFormat("RSICYCLE_%I64d",g_cycle_counter),"BUY2_REJECT_PATTERN",2,t,r1,atr,b.close,g_common_stop,StringFormat("div=%s|retest=%s",divergence?"YES":"NO",retest?"YES":"NO"));
               g_state=RS_ACTIVE;g_second_min=1000;g_second_low=1e100;return;
            }
         }
      }
      return;
   }

   if(g_state==RS_COOLDOWN){if(r1>=RESET_RSI)g_state=RS_IDLE;return;}
   if(g_state==RS_IDLE)
   {
      if(r2>=OVERSOLD&&r1<OVERSOLD){g_state=RS_ARMED1;g_episode_min=r1;g_episode_low=b.low;LogEvent("", "ARM_BUY1",1,t,r1,atr,b.close,0,"");}
      return;
   }
   if(g_state==RS_ARMED1)
   {
      g_episode_min=MathMin(g_episode_min,r1);g_episode_low=MathMin(g_episode_low,b.low);
      if(r2<=OVERSOLD&&r1>OVERSOLD)
      {
         g_cycle_counter++;g_first_min=g_episode_min;g_first_low=MathMin(g_episode_low,b.low);double stop=g_first_low-SL_BUFFER_ATR*atr;
         if(CreateLeg(1,stop,atr,r1,StringFormat("minRSI=%.2f|episodeLow=%.5f",g_first_min,g_first_low))){g_cycle_active=true;g_cycle_start=t;g_legs=1;g_state=RS_ACTIVE;}
         else {g_cycle_active=false;g_state=RS_COOLDOWN;}
         g_episode_min=1000;g_episode_low=1e100;return;
      }
   }
}

void ProcessM1()
{
   datetime o=iTime(_Symbol,PERIOD_M1,1);if(o<=0||o==g_last_m1_open)return;MqlRates b[1];if(CopyRates(_Symbol,PERIOD_M1,1,1,b)!=1)return;double r1=Buf(g_rsi,1),r2=Buf(g_rsi,2),atr=Buf(g_atr,1);if(r1==EMPTY_VALUE||r2==EMPTY_VALUE||atr==EMPTY_VALUE||atr<=0)return;g_last_m1_open=o;datetime t=b[0].time+60;
   for(int i=0;i<MAX_TRACKED;i++)if(g_trades[i].active)ProcessPath(g_trades[i],b[0],t);
   ProcessRSIState(b[0],r1,r2,atr,t);
}

int OnInit()
{
   g_rsi=iRSI(_Symbol,PERIOD_M1,RSI_PERIOD,PRICE_CLOSE);g_atr=iATR(_Symbol,PERIOD_M1,ATR_PERIOD);if(g_rsi==INVALID_HANDLE||g_atr==INVALID_HANDLE)return INIT_FAILED;
   g_session=StringFormat("RSI111611_%s_%I64d_%I64d",_Symbol,(long)TimeCurrent(),(long)GetTickCount64());EnsureFolder();for(int i=0;i<MAX_TRACKED;i++)g_trades[i].active=false;g_last_m1_open=iTime(_Symbol,PERIOD_M1,1);
   Print("[RSI111611] START ",_Symbol," | CLOSED-BAR LEGACY | NO ORDERS");return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){if(g_rsi!=INVALID_HANDLE)IndicatorRelease(g_rsi);if(g_atr!=INVALID_HANDLE)IndicatorRelease(g_atr);}
void OnTick(){ProcessM1();}
