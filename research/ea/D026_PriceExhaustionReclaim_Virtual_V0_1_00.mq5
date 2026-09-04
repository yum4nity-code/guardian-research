#property strict
#property version   "1.00"
#property description "D026 Price Exhaustion Reclaim Virtual V0 1.00 - price-only, no orders"

// D026 Price Exhaustion Reclaim
// Pure virtual Strategy Tester observer.
// - NEW strategy branch, frozen before D026 results.
// - Price/time/ATR only: no tick-volume or external-data gating.
// - No CTrade include and no order/position functions.
// - No dependence on balance, margin, lot minimums or execution success.
// - Virtual entry = validating CLOSED M15 close.
// - Structural SL is observational only.
// - Tracks +0.5R, +1R..+5R, first original-SL touch,
//   and first return to entry after +1R (BE-after-1R path).

input int  InpMaxHoldHours = 48;
input int  InpTimerSeconds = 1;
input bool InpVerbose      = true;

enum PerState
{
   PER_IDLE = 0,
   PER_WATCH = 1,
   PER_SWEEP = 2,
   PER_DISPLACEMENT = 3,
   PER_EXHAUSTION = 4,
   PER_RECLAIM = 5
};

enum LerSide
{
   SIDE_LONG = 1,
   SIDE_SHORT = -1
};

#define LEVEL_COUNT 8
#define MAX_TRACKERS LEVEL_COUNT
#define MAX_TRACKED_TRADES 256

#define WATCH_ATR                 0.50
#define SWEEP_MIN_ATR             0.10
#define STOP_BUFFER_ATR           0.10
#define DISP_RANGE_SHOCK          1.25
#define DISP_BODY_ATR             0.20
#define DISP_BODY_EFF             0.55
#define DISP_CLOSE_LOC_LONG_MAX   0.30
#define DISP_CLOSE_LOC_SHORT_MIN  0.70
#define EXHAUST_PROGRESS_FRAC     0.20
#define EXHAUST_RANGE_FRAC        0.80
#define RETEST_ATR                0.15
#define COOLDOWN_SECONDS          (4*60*60)

struct LevelTracker
{
   int level_index;
   PerState state;
   double level_price;
   double frozen_level;
   datetime cooldown_until_utc;
   int bars_in_state;
   string event_id;
   datetime event_utc;
   datetime sweep_server_close;
   datetime sweep_utc;
   double atr_h1;
   double sweep_extreme;
   double sweep_depth_atr;
   double displacement_range;
   double displacement_range_shock;
   double displacement_body_atr;
   double displacement_body_eff;
   double displacement_close_loc;
   double last_outward_extreme;
   datetime reclaim_utc;
   int acceptance_closes;
   string validation_path;
};

struct TrackedTrade
{
   bool active;
   string event_id;
   LerSide side;
   datetime entry_utc;
   datetime entry_server_time;
   double entry;
   double stop;
   double risk;
   double mfe_r;
   double mae_r;
   datetime hit05_utc;
   datetime hit1_utc;
   datetime hit2_utc;
   datetime hit3_utc;
   datetime hit4_utc;
   datetime hit5_utc;
   datetime stop_utc;
   datetime be_after1_utc;
   bool be_after1_ambiguous_same_m1;
   bool ambiguous;
   bool h1_logged;
   bool h4_logged;
   bool h8_logged;
   bool h24_logged;
   bool h48_logged;
};

LevelTracker g_trackers[MAX_TRACKERS];
TrackedTrade g_trades[MAX_TRACKED_TRADES];
int g_atr_h1_handle = INVALID_HANDLE;
datetime g_last_m15_closed_open = 0;
datetime g_last_m1_closed_open = 0;
long g_event_counter = 0;
string g_session_id = "";
datetime g_last_review_log_utc = 0;

string SideName(LerSide side)
{
   return (side == SIDE_LONG ? "LONG" : "SHORT");
}

string LevelName(int idx)
{
   switch(idx)
   {
      case 0: return "PDH";
      case 1: return "PDL";
      case 2: return "PWH";
      case 3: return "PWL";
      case 4: return "H1_SWING_HIGH";
      case 5: return "H1_SWING_LOW";
      case 6: return "H4_SWING_HIGH";
      case 7: return "H4_SWING_LOW";
   }
   return "UNKNOWN";
}

LerSide LevelSide(int idx)
{
   if(idx == 1 || idx == 3 || idx == 5 || idx == 7)
      return SIDE_LONG;
   return SIDE_SHORT;
}

void EnsureCommonFolder()
{
   FolderCreate("GuardianResearch", FILE_COMMON);
   FolderCreate("GuardianResearch\\D026", FILE_COMMON);
}

string EventsFile()
{
   return "GuardianResearch\\D026\\d026_per_virtual_v0_events.csv";
}

string TradesFile()
{
   return "GuardianResearch\\D026\\d026_per_virtual_v0_trades.csv";
}

string OutcomesFile()
{
   return "GuardianResearch\\D026\\d026_per_virtual_v0_outcomes.csv";
}

void LogReview(string msg)
{
   datetime now = TimeGMT();
   if(now - g_last_review_log_utc < 60)
      return;
   g_last_review_log_utc = now;
   Print("[D026V][REVIEW] ",msg);
}

void LogEvent(LevelTracker &tr,string transition,datetime utc_time,datetime server_bar_close,
              double range_shock,double body_atr,double body_eff,double close_loc,
              double extra_progress_frac,double exhaust_range_frac)
{
   EnsureCommonFolder();
   int h = FileOpen(EventsFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h == INVALID_HANDLE) return;
   if(FileSize(h) == 0)
      FileWrite(h,"session_id","event_id","utc_epoch","utc_text","server_bar_close","symbol","level_family","side","transition",
                  "level_price","atr_h1","sweep_depth_atr","range_shock","body_atr","body_eff","close_loc",
                  "displacement_range","extra_progress_frac","exhaust_range_frac","sequence_elapsed_min","reclaim_delay_min",
                  "sweep_extreme","validation_path");
   double sequence_elapsed_min=(tr.sweep_utc>0 ? (double)(utc_time-tr.sweep_utc)/60.0 : -1.0);
   double reclaim_delay_min=(tr.reclaim_utc>0 && tr.sweep_utc>0 ? (double)(tr.reclaim_utc-tr.sweep_utc)/60.0 : -1.0);
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session_id,tr.event_id,(long)utc_time,TimeToString(utc_time,TIME_DATE|TIME_SECONDS),
             TimeToString(server_bar_close,TIME_DATE|TIME_SECONDS),_Symbol,LevelName(tr.level_index),SideName(LevelSide(tr.level_index)),transition,
             DoubleToString(tr.frozen_level,_Digits),DoubleToString(tr.atr_h1,8),DoubleToString(tr.sweep_depth_atr,6),
             DoubleToString(range_shock,6),DoubleToString(body_atr,6),DoubleToString(body_eff,6),DoubleToString(close_loc,6),
             DoubleToString(tr.displacement_range,8),DoubleToString(extra_progress_frac,6),DoubleToString(exhaust_range_frac,6),
             DoubleToString(sequence_elapsed_min,2),DoubleToString(reclaim_delay_min,2),
             DoubleToString(tr.sweep_extreme,_Digits),tr.validation_path);
   FileFlush(h);
   FileClose(h);
}

void LogTrade(TrackedTrade &vt,string level_family,string path)
{
   EnsureCommonFolder();
   int h = FileOpen(TradesFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h == INVALID_HANDLE) return;
   if(FileSize(h) == 0)
      FileWrite(h,"session_id","event_id","entry_utc","symbol","side","level_family","path","entry","sl","risk_price");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session_id,vt.event_id,TimeToString(vt.entry_utc,TIME_DATE|TIME_SECONDS),_Symbol,SideName(vt.side),level_family,path,
             DoubleToString(vt.entry,_Digits),DoubleToString(vt.stop,_Digits),DoubleToString(vt.risk,_Digits));
   FileFlush(h);
   FileClose(h);
}

void LogOutcome(TrackedTrade &vt,string horizon,datetime utc_time)
{
   EnsureCommonFolder();
   int h = FileOpen(OutcomesFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h == INVALID_HANDLE) return;
   if(FileSize(h) == 0)
      FileWrite(h,"session_id","event_id","utc_text","symbol","side","horizon","mfe_r","mae_r","hit05_utc",
                  "hit1_utc","hit2_utc","hit3_utc","hit4_utc","hit5_utc","stop_utc","be_after1_utc",
                  "be_after1_ambiguous_same_m1","ambiguous_same_m1");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session_id,vt.event_id,TimeToString(utc_time,TIME_DATE|TIME_SECONDS),_Symbol,SideName(vt.side),horizon,
             DoubleToString(vt.mfe_r,6),DoubleToString(vt.mae_r,6),(long)vt.hit05_utc,
             (long)vt.hit1_utc,(long)vt.hit2_utc,(long)vt.hit3_utc,(long)vt.hit4_utc,(long)vt.hit5_utc,
             (long)vt.stop_utc,(long)vt.be_after1_utc,
             (vt.be_after1_ambiguous_same_m1 ? "YES" : "NO"),(vt.ambiguous ? "YES" : "NO"));
   FileFlush(h);
   FileClose(h);
}

bool GetAtrH1(double &atr)
{
   atr = 0.0;
   if(g_atr_h1_handle == INVALID_HANDLE) return false;
   double buf[1];
   if(CopyBuffer(g_atr_h1_handle,0,1,1,buf) != 1) return false;
   atr = buf[0];
   return (atr > 0.0);
}

bool GetM15Stats(MqlRates &bar,MqlRates &prev,double &range_shock)
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M15,0,22,rates) < 22) return false;
   bar = rates[1];
   prev = rates[2];
   double mean_range = 0.0;
   for(int i=2;i<=21;i++)
      mean_range += rates[i].high-rates[i].low;
   mean_range /= 20.0;
   if(mean_range <= 0.0) return false;
   range_shock = (bar.high-bar.low)/mean_range;
   return true;
}

bool FindLatestSwing(ENUM_TIMEFRAMES tf,bool want_high,double &price)
{
   price = 0.0;
   int bars = Bars(_Symbol,tf);
   if(bars < 20) return false;
   int max_shift = MathMin(120,bars-3);
   for(int s=3;s<=max_shift;s++)
   {
      double p = (want_high ? iHigh(_Symbol,tf,s) : iLow(_Symbol,tf,s));
      if(p <= 0.0) continue;
      bool pivot = false;
      if(want_high)
         pivot = (p > iHigh(_Symbol,tf,s-1) && p > iHigh(_Symbol,tf,s-2) && p > iHigh(_Symbol,tf,s+1) && p > iHigh(_Symbol,tf,s+2));
      else
         pivot = (p < iLow(_Symbol,tf,s-1) && p < iLow(_Symbol,tf,s-2) && p < iLow(_Symbol,tf,s+1) && p < iLow(_Symbol,tf,s+2));
      if(pivot) { price = p; return true; }
   }
   return false;
}

bool GetLevelPrice(int level_index,double &price)
{
   price = 0.0;
   switch(level_index)
   {
      case 0: price=iHigh(_Symbol,PERIOD_D1,1); return price>0.0;
      case 1: price=iLow(_Symbol,PERIOD_D1,1);  return price>0.0;
      case 2: price=iHigh(_Symbol,PERIOD_W1,1); return price>0.0;
      case 3: price=iLow(_Symbol,PERIOD_W1,1);  return price>0.0;
      case 4: return FindLatestSwing(PERIOD_H1,true,price);
      case 5: return FindLatestSwing(PERIOD_H1,false,price);
      case 6: return FindLatestSwing(PERIOD_H4,true,price);
      case 7: return FindLatestSwing(PERIOD_H4,false,price);
   }
   return false;
}

void ResetTracker(LevelTracker &tr,bool apply_cooldown)
{
   if(apply_cooldown) tr.cooldown_until_utc = TimeGMT()+COOLDOWN_SECONDS;
   tr.state=PER_IDLE; tr.bars_in_state=0; tr.event_id=""; tr.event_utc=0; tr.sweep_server_close=0; tr.sweep_utc=0;
   tr.frozen_level=0.0; tr.atr_h1=0.0; tr.sweep_extreme=0.0; tr.sweep_depth_atr=0.0; tr.displacement_range=0.0;
   tr.displacement_range_shock=0.0; tr.displacement_body_atr=0.0; tr.displacement_body_eff=0.0; tr.displacement_close_loc=0.0;
   tr.last_outward_extreme=0.0; tr.reclaim_utc=0; tr.acceptance_closes=0; tr.validation_path="";
}

bool IsDisplacement(LerSide side,MqlRates &bar,double atr,double range_shock,
                    double &body_atr,double &body_eff,double &close_loc)
{
   if(atr<=0.0) return false;
   double range=bar.high-bar.low;
   if(range<=0.0) return false;
   double directional_body=(side==SIDE_LONG ? bar.open-bar.close : bar.close-bar.open);
   if(directional_body<=0.0) return false;
   body_atr=directional_body/atr;
   body_eff=directional_body/range;
   close_loc=(bar.close-bar.low)/range;
   bool close_ok=(side==SIDE_LONG ? close_loc<=DISP_CLOSE_LOC_LONG_MAX : close_loc>=DISP_CLOSE_LOC_SHORT_MIN);
   return (range_shock>=DISP_RANGE_SHOCK && body_atr>=DISP_BODY_ATR && body_eff>=DISP_BODY_EFF && close_ok);
}

void TransitionDisplacement(LevelTracker &tr,MqlRates &bar,double range_shock,double body_atr,double body_eff,double close_loc,datetime utc_now)
{
   tr.state=PER_DISPLACEMENT; tr.bars_in_state=0; tr.displacement_range=bar.high-bar.low;
   tr.displacement_range_shock=range_shock; tr.displacement_body_atr=body_atr;
   tr.displacement_body_eff=body_eff; tr.displacement_close_loc=close_loc;
   LerSide side=LevelSide(tr.level_index);
   if(side==SIDE_LONG) { tr.sweep_extreme=MathMin(tr.sweep_extreme,bar.low); tr.last_outward_extreme=tr.sweep_extreme; }
   else { tr.sweep_extreme=MathMax(tr.sweep_extreme,bar.high); tr.last_outward_extreme=tr.sweep_extreme; }
   LogEvent(tr,"DISPLACEMENT",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,body_atr,body_eff,close_loc,-1.0,-1.0);
   if(InpVerbose) Print("[D026V][",_Symbol,"][",LevelName(tr.level_index),"] DISPLACEMENT event=",tr.event_id);
}

int FindFreeTradeSlot()
{
   for(int i=0;i<MAX_TRACKED_TRADES;i++) if(!g_trades[i].active) return i;
   return -1;
}

void CreateVirtualTrade(LevelTracker &tr,MqlRates &bar,string path,datetime utc_now)
{
   LerSide side=LevelSide(tr.level_index);
   double stop=(side==SIDE_LONG ? tr.sweep_extreme-STOP_BUFFER_ATR*tr.atr_h1 : tr.sweep_extreme+STOP_BUFFER_ATR*tr.atr_h1);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double entry=bar.close;
   double risk=MathAbs(entry-stop);
   if(risk<=0.0 || point<=0.0 || risk<5.0*point)
   {
      LogEvent(tr,"VALID_SIGNAL_REJECTED_BAD_RISK",utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1,-1,-1);
      ResetTracker(tr,true);
      return;
   }
   int slot=FindFreeTradeSlot();
   if(slot<0)
   {
      LogEvent(tr,"VALID_SIGNAL_REJECTED_NO_SLOT",utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1,-1,-1);
      Print("[D026V][NO_SLOT] increase MAX_TRACKED_TRADES if this appears");
      ResetTracker(tr,true);
      return;
   }

   tr.validation_path=path;
   LogEvent(tr,"VALID_SIGNAL_"+path,utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1,-1,-1);

   TrackedTrade vt;
   vt.active=true; vt.event_id=tr.event_id; vt.side=side; vt.entry_utc=utc_now;
   vt.entry_server_time=bar.time+PeriodSeconds(PERIOD_M15);
   vt.entry=entry; vt.stop=stop; vt.risk=risk;
   vt.mfe_r=0.0; vt.mae_r=0.0;
   vt.hit05_utc=0; vt.hit1_utc=0; vt.hit2_utc=0; vt.hit3_utc=0; vt.hit4_utc=0; vt.hit5_utc=0;
   vt.stop_utc=0; vt.be_after1_utc=0;
   vt.be_after1_ambiguous_same_m1=false; vt.ambiguous=false;
   vt.h1_logged=false; vt.h4_logged=false; vt.h8_logged=false; vt.h24_logged=false; vt.h48_logged=false;
   g_trades[slot]=vt;
   LogTrade(g_trades[slot],LevelName(tr.level_index),path);
   Print("[D026V][VALID_SIGNAL] event=",tr.event_id," side=",SideName(side)," level=",LevelName(tr.level_index),
         " path=",path," entry=",DoubleToString(entry,_Digits)," sl=",DoubleToString(stop,_Digits));
   ResetTracker(tr,true);
}

void FailSequence(LevelTracker &tr,string reason,MqlRates &bar,datetime utc_now)
{
   LogEvent(tr,"FAILED_"+reason,utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1,-1,-1);
   if(InpVerbose) Print("[D026V][",_Symbol,"][",LevelName(tr.level_index),"] failed=",reason," event=",tr.event_id);
   ResetTracker(tr,true);
}

void ProcessTracker(LevelTracker &tr,MqlRates &bar,MqlRates &prev,double atr,double range_shock,datetime utc_now)
{
   LerSide side=LevelSide(tr.level_index);
   if(tr.state==PER_IDLE || tr.state==PER_WATCH)
   {
      if(utc_now<tr.cooldown_until_utc) return;
      double live_level=0.0;
      if(!GetLevelPrice(tr.level_index,live_level) || live_level<=0.0) return;
      tr.level_price=live_level;
      double dist=MathAbs(bar.close-live_level);
      if(tr.state==PER_IDLE && dist<=WATCH_ATR*atr)
      {
         tr.state=PER_WATCH; tr.frozen_level=live_level; tr.atr_h1=atr; tr.event_id="";
         LogEvent(tr,"LEVEL_WATCH",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,-1.0,-1.0,-1.0,-1.0,-1.0);
      }
      else if(tr.state==PER_WATCH && dist>2.0*WATCH_ATR*atr)
      {
         ResetTracker(tr,false); return;
      }

      bool fresh_sweep=false; double depth=0.0;
      if(side==SIDE_LONG)
      {
         fresh_sweep=(prev.close>=live_level && bar.low<=live_level-SWEEP_MIN_ATR*atr);
         if(fresh_sweep) depth=(live_level-bar.low)/atr;
      }
      else
      {
         fresh_sweep=(prev.close<=live_level && bar.high>=live_level+SWEEP_MIN_ATR*atr);
         if(fresh_sweep) depth=(bar.high-live_level)/atr;
      }
      if(!fresh_sweep) return;

      tr.state=PER_SWEEP; tr.bars_in_state=0; tr.frozen_level=live_level; tr.atr_h1=atr; tr.sweep_depth_atr=depth;
      tr.sweep_utc=utc_now; tr.event_utc=utc_now; tr.sweep_server_close=bar.time+PeriodSeconds(PERIOD_M15);
      tr.sweep_extreme=(side==SIDE_LONG ? bar.low : bar.high); tr.last_outward_extreme=tr.sweep_extreme;
      g_event_counter++;
      tr.event_id=StringFormat("D026_%s_%s_%I64d_%I64d",_Symbol,LevelName(tr.level_index),(long)utc_now,g_event_counter);
      LogEvent(tr,"SWEEP",utc_now,tr.sweep_server_close,range_shock,-1.0,-1.0,-1.0,-1.0,-1.0);
      if(InpVerbose) Print("[D026V][",_Symbol,"][",LevelName(tr.level_index),"] SWEEP event=",tr.event_id," depthATR=",DoubleToString(depth,3));

      double body_atr=0.0,body_eff=0.0,close_loc=0.0;
      if(IsDisplacement(side,bar,atr,range_shock,body_atr,body_eff,close_loc))
         TransitionDisplacement(tr,bar,range_shock,body_atr,body_eff,close_loc,utc_now);
      return;
   }

   if(side==SIDE_LONG) tr.sweep_extreme=MathMin(tr.sweep_extreme,bar.low);
   else tr.sweep_extreme=MathMax(tr.sweep_extreme,bar.high);
   tr.bars_in_state++;

   if(tr.state==PER_SWEEP)
   {
      double body_atr=0.0,body_eff=0.0,close_loc=0.0;
      if(IsDisplacement(side,bar,atr,range_shock,body_atr,body_eff,close_loc))
      {
         TransitionDisplacement(tr,bar,range_shock,body_atr,body_eff,close_loc,utc_now);
         return;
      }
      if(tr.bars_in_state>2) FailSequence(tr,"NO_DISPLACEMENT_2BARS",bar,utc_now);
      return;
   }

   if(tr.state==PER_DISPLACEMENT)
   {
      double progress=0.0;
      if(side==SIDE_LONG && bar.low<tr.last_outward_extreme) progress=tr.last_outward_extreme-bar.low;
      if(side==SIDE_SHORT && bar.high>tr.last_outward_extreme) progress=bar.high-tr.last_outward_extreme;
      double progress_frac=(tr.displacement_range>0.0 ? progress/tr.displacement_range : 999.0);
      double range_frac=(tr.displacement_range>0.0 ? (bar.high-bar.low)/tr.displacement_range : 999.0);

      if(progress_frac<=EXHAUST_PROGRESS_FRAC && range_frac<=EXHAUST_RANGE_FRAC)
      {
         tr.state=PER_EXHAUSTION; tr.bars_in_state=0;
         if(side==SIDE_LONG) tr.last_outward_extreme=MathMin(tr.last_outward_extreme,bar.low);
         else tr.last_outward_extreme=MathMax(tr.last_outward_extreme,bar.high);
         LogEvent(tr,"EXHAUSTION",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,-1.0,-1.0,-1.0,progress_frac,range_frac);
         if(InpVerbose) Print("[D026V][",_Symbol,"][",LevelName(tr.level_index),"] EXHAUSTION event=",tr.event_id,
                              " progress=",DoubleToString(progress_frac,3)," rangeFrac=",DoubleToString(range_frac,3));
         return;
      }
      if(side==SIDE_LONG) tr.last_outward_extreme=MathMin(tr.last_outward_extreme,bar.low);
      else tr.last_outward_extreme=MathMax(tr.last_outward_extreme,bar.high);
      if(tr.bars_in_state>3) FailSequence(tr,"NO_EXHAUSTION_3BARS",bar,utc_now);
      return;
   }

   if(tr.state==PER_EXHAUSTION)
   {
      bool reclaimed=(side==SIDE_LONG ? bar.close>tr.frozen_level : bar.close<tr.frozen_level);
      if(reclaimed)
      {
         tr.state=PER_RECLAIM; tr.bars_in_state=0; tr.reclaim_utc=utc_now; tr.acceptance_closes=1;
         LogEvent(tr,"RECLAIM",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,-1.0,-1.0,-1.0,-1.0,-1.0);
         return;
      }
      if(tr.bars_in_state>4) FailSequence(tr,"NO_RECLAIM_4BARS",bar,utc_now);
      return;
   }

   if(tr.state==PER_RECLAIM)
   {
      bool inside_close=(side==SIDE_LONG ? bar.close>tr.frozen_level : bar.close<tr.frozen_level);
      bool retest=(side==SIDE_LONG ? (bar.low<=tr.frozen_level+RETEST_ATR*tr.atr_h1 && bar.close>tr.frozen_level)
                                  : (bar.high>=tr.frozen_level-RETEST_ATR*tr.atr_h1 && bar.close<tr.frozen_level));
      if(retest) { CreateVirtualTrade(tr,bar,"RETEST",utc_now); return; }
      if(inside_close) tr.acceptance_closes++; else tr.acceptance_closes=0;
      if(tr.acceptance_closes>=2) { CreateVirtualTrade(tr,bar,"ACCEPTANCE",utc_now); return; }
      if(tr.bars_in_state>4) FailSequence(tr,"NO_RETEST_ACCEPTANCE_4BARS",bar,utc_now);
   }
}

void ProcessM15()
{
   datetime closed_open=iTime(_Symbol,PERIOD_M15,1);
   if(closed_open<=0 || closed_open==g_last_m15_closed_open) return;
   MqlRates bar,prev; double range_shock=0.0;
   if(!GetM15Stats(bar,prev,range_shock)) { LogReview("insufficient M15 price history"); return; }
   double atr=0.0;
   if(!GetAtrH1(atr)) { LogReview("H1 ATR unavailable"); return; }
   g_last_m15_closed_open=closed_open;
   datetime utc_now=TimeGMT();
   for(int i=0;i<LEVEL_COUNT;i++) ProcessTracker(g_trackers[i],bar,prev,atr,range_shock,utc_now);
}

void SetHitIfNeeded(TrackedTrade &vt,int r,datetime utc_now)
{
   if(r==1 && vt.hit1_utc==0) vt.hit1_utc=utc_now;
   if(r==2 && vt.hit2_utc==0) vt.hit2_utc=utc_now;
   if(r==3 && vt.hit3_utc==0) vt.hit3_utc=utc_now;
   if(r==4 && vt.hit4_utc==0) vt.hit4_utc=utc_now;
   if(r==5 && vt.hit5_utc==0) vt.hit5_utc=utc_now;
}

bool AlreadyHit(TrackedTrade &vt,int r)
{
   if(r==1) return vt.hit1_utc!=0;
   if(r==2) return vt.hit2_utc!=0;
   if(r==3) return vt.hit3_utc!=0;
   if(r==4) return vt.hit4_utc!=0;
   if(r==5) return vt.hit5_utc!=0;
   return true;
}

void ProcessTradeBar(TrackedTrade &vt,MqlRates &bar,datetime utc_now)
{
   datetime bar_close_server=bar.time+PeriodSeconds(PERIOD_M1);
   if(bar_close_server<=vt.entry_server_time || vt.risk<=0.0) return;

   double fav=0.0,adv=0.0;
   if(vt.side==SIDE_LONG)
   {
      fav=MathMax(0.0,bar.high-vt.entry)/vt.risk;
      adv=MathMax(0.0,vt.entry-bar.low)/vt.risk;
   }
   else
   {
      fav=MathMax(0.0,vt.entry-bar.low)/vt.risk;
      adv=MathMax(0.0,bar.high-vt.entry)/vt.risk;
   }
   vt.mfe_r=MathMax(vt.mfe_r,fav);
   vt.mae_r=MathMax(vt.mae_r,adv);

   bool stop_cross=false;
   if(vt.stop_utc==0)
      stop_cross=(vt.side==SIDE_LONG ? bar.low<=vt.stop : bar.high>=vt.stop);

   bool new_positive_hit=false;
   bool new_runner_target_hit=false;
   bool had_hit1_before=(vt.hit1_utc!=0);

   if(vt.hit05_utc==0)
   {
      double target05=(vt.side==SIDE_LONG ? vt.entry+0.5*vt.risk : vt.entry-0.5*vt.risk);
      bool crossed05=(vt.side==SIDE_LONG ? bar.high>=target05 : bar.low<=target05);
      if(crossed05)
      {
         vt.hit05_utc=utc_now;
         new_positive_hit=true;
      }
   }

   for(int r=1;r<=5;r++)
   {
      if(AlreadyHit(vt,r)) continue;
      double target=(vt.side==SIDE_LONG ? vt.entry+r*vt.risk : vt.entry-r*vt.risk);
      bool crossed=(vt.side==SIDE_LONG ? bar.high>=target : bar.low<=target);
      if(crossed)
      {
         SetHitIfNeeded(vt,r,utc_now);
         new_positive_hit=true;
         if(r>=2) new_runner_target_hit=true;
      }
   }

   bool hit1_this_bar=(!had_hit1_before && vt.hit1_utc!=0);
   if(vt.be_after1_utc==0 && (had_hit1_before || hit1_this_bar))
   {
      bool be_cross=(vt.side==SIDE_LONG ? bar.low<=vt.entry : bar.high>=vt.entry);
      if(be_cross)
      {
         vt.be_after1_utc=utc_now;
         if(hit1_this_bar || new_runner_target_hit)
         {
            vt.be_after1_ambiguous_same_m1=true;
            if(InpVerbose) Print("[D026V][AMBIGUOUS_BE_PATH_M1] event=",vt.event_id);
         }
      }
   }

   if(stop_cross)
   {
      vt.stop_utc=utc_now;
      if(new_positive_hit)
      {
         vt.ambiguous=true;
         if(InpVerbose) Print("[D026V][AMBIGUOUS_M1] event=",vt.event_id);
      }
   }

   long elapsed=(long)(utc_now-vt.entry_utc);
   if(!vt.h1_logged && elapsed>=3600) { vt.h1_logged=true; LogOutcome(vt,"1H",utc_now); }
   if(!vt.h4_logged && elapsed>=4*3600) { vt.h4_logged=true; LogOutcome(vt,"4H",utc_now); }
   if(!vt.h8_logged && elapsed>=8*3600) { vt.h8_logged=true; LogOutcome(vt,"8H",utc_now); }
   if(!vt.h24_logged && elapsed>=24*3600) { vt.h24_logged=true; LogOutcome(vt,"24H",utc_now); }
   if(!vt.h48_logged && elapsed>=InpMaxHoldHours*3600)
   {
      vt.h48_logged=true;
      LogOutcome(vt,StringFormat("%dH",InpMaxHoldHours),utc_now);
      Print("[D026V][COMPLETE] event=",vt.event_id,
            " MFE=",DoubleToString(vt.mfe_r,2),"R MAE=",DoubleToString(vt.mae_r,2),"R",
            " hit05=",(long)vt.hit05_utc," hit1=",(long)vt.hit1_utc," be_after1=",(long)vt.be_after1_utc);
      vt.active=false;
   }
}

void ProcessM1()
{
   datetime closed_open=iTime(_Symbol,PERIOD_M1,1);
   if(closed_open<=0 || closed_open==g_last_m1_closed_open) return;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M1,0,2,rates)<2) return;
   g_last_m1_closed_open=closed_open;
   datetime utc_now=TimeGMT();
   for(int i=0;i<MAX_TRACKED_TRADES;i++)
      if(g_trades[i].active) ProcessTradeBar(g_trades[i],rates[1],utc_now);
}

int OnInit()
{
   if(InpMaxHoldHours<=0 || InpTimerSeconds<=0) return INIT_PARAMETERS_INCORRECT;
   if(!SymbolSelect(_Symbol,true)) return INIT_FAILED;
   g_atr_h1_handle=iATR(_Symbol,PERIOD_H1,14);
   if(g_atr_h1_handle==INVALID_HANDLE)
   {
      Print("[D026V][FATAL] cannot create H1 ATR handle for ",_Symbol," error=",GetLastError());
      return INIT_FAILED;
   }
   g_session_id=StringFormat("D026V100_%s_%I64d_%I64d",_Symbol,(long)TimeGMT(),(long)GetTickCount64());
   for(int i=0;i<LEVEL_COUNT;i++)
   {
      g_trackers[i].level_index=i;
      g_trackers[i].cooldown_until_utc=0;
      ResetTracker(g_trackers[i],false);
   }
   for(int i=0;i<MAX_TRACKED_TRADES;i++) g_trades[i].active=false;
   EnsureCommonFolder();
   EventSetTimer(MathMax(1,InpTimerSeconds));
   Print("[D026V][START] Price Exhaustion Reclaim V0 1.00 symbol=",_Symbol," max_hold=",InpMaxHoldHours,
         "h | PRICE_ONLY | NO_VOLUME | NO_ORDERS | RULES_LOCKED_PRE_RESULT");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_atr_h1_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_h1_handle);
   Print("[D026V][STOP] reason=",reason);
}

void OnTimer()
{
   ProcessM15();
   ProcessM1();
}

void OnTick()
{
   // Timer-driven, closed-bar logic only.
}
