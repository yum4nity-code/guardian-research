#property strict
#property version   "1.01"
#property description "D025 LER Trading 1.01 - single-symbol MT5 backtest/trading EA"

#include <Trade/Trade.mqh>

// D025 Liquidity Exhaustion Reclaim
// Trading implementation of the locked V0 signal state machine.
// Select BTCUSD or ETHUSD directly in MT5 Strategy Tester: the EA trades _Symbol only.
// Entry: VALID_SIGNAL (RETEST or ACCEPTANCE)
// Exit: structural SL or forced close after InpMaxHoldHours. No TP.

input double InpRiskPercent = 0.50;
input int    InpMaxHoldHours = 48;
input ulong  InpMagic        = 25090401;
input int    InpTimerSeconds = 1;
input bool   InpVerbose      = true;

enum LerState
{
   LER_IDLE = 0,
   LER_WATCH = 1,
   LER_SWEEP = 2,
   LER_CASCADE = 3,
   LER_EXHAUSTION = 4,
   LER_RECLAIM = 5
};

enum LerSide
{
   SIDE_LONG = 1,
   SIDE_SHORT = -1
};

#define LEVEL_COUNT 8
#define MAX_TRACKERS LEVEL_COUNT
#define MAX_TRACKED_TRADES 64

#define WATCH_ATR              0.50
#define SWEEP_MIN_ATR          0.10
#define STOP_BUFFER_ATR        0.10
#define CASCADE_RANGE_SHOCK    1.25
#define CASCADE_BODY_ATR       0.15
#define CASCADE_RELVOL         1.25
#define EXHAUST_PROGRESS_FRAC  0.25
#define EXHAUST_ACTIVITY_FRAC  0.70
#define RETEST_ATR             0.15
#define COOLDOWN_SECONDS       (4*60*60)

struct LevelTracker
{
   int level_index;
   LerState state;
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
   double cascade_range;
   long cascade_volume;
   double cascade_range_shock;
   double cascade_body_atr;
   double cascade_relvol;
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
   double volume;
   ulong position_id;
   double mfe_r;
   double mae_r;
   datetime hit1_utc;
   datetime hit2_utc;
   datetime hit3_utc;
   datetime hit4_utc;
   datetime hit5_utc;
   datetime stop_utc;
   bool ambiguous;
   bool h1_logged;
   bool h4_logged;
   bool h8_logged;
   bool h24_logged;
   bool h48_logged;
};

CTrade g_trade;
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
   FolderCreate("GuardianResearch\\D025", FILE_COMMON);
}

string EventsFile()
{
   return "GuardianResearch\\D025\\d025_ler_trading_1_01_events.csv";
}

string TradesFile()
{
   return "GuardianResearch\\D025\\d025_ler_trading_1_01_trades.csv";
}

string OutcomesFile()
{
   return "GuardianResearch\\D025\\d025_ler_trading_1_01_outcomes.csv";
}

void LogReview(string msg)
{
   datetime now = TimeGMT();
   if(now - g_last_review_log_utc < 60)
      return;
   g_last_review_log_utc = now;
   Print("[D025T][REVIEW] ",msg);
}

void LogEvent(LevelTracker &tr,string transition,datetime utc_time,datetime server_bar_close,
              double range_shock,double body_atr,double relvol,double extra_progress_frac)
{
   EnsureCommonFolder();
   int h = FileOpen(EventsFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h == INVALID_HANDLE) return;
   if(FileSize(h) == 0)
      FileWrite(h,"session_id","event_id","utc_epoch","utc_text","server_bar_close","symbol","level_family","side","transition",
                  "level_price","atr_h1","sweep_depth_atr","range_shock","body_atr","rel_tick_volume","extra_progress_frac",
                  "sweep_extreme","validation_path");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session_id,tr.event_id,(long)utc_time,TimeToString(utc_time,TIME_DATE|TIME_SECONDS),
             TimeToString(server_bar_close,TIME_DATE|TIME_SECONDS),_Symbol,LevelName(tr.level_index),SideName(LevelSide(tr.level_index)),transition,
             DoubleToString(tr.frozen_level,_Digits),DoubleToString(tr.atr_h1,8),DoubleToString(tr.sweep_depth_atr,6),
             DoubleToString(range_shock,6),DoubleToString(body_atr,6),DoubleToString(relvol,6),DoubleToString(extra_progress_frac,6),
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
      FileWrite(h,"session_id","event_id","entry_utc","symbol","side","level_family","path","entry","sl","risk_price","volume","position_id");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session_id,vt.event_id,TimeToString(vt.entry_utc,TIME_DATE|TIME_SECONDS),_Symbol,SideName(vt.side),level_family,path,
             DoubleToString(vt.entry,_Digits),DoubleToString(vt.stop,_Digits),DoubleToString(vt.risk,_Digits),
             DoubleToString(vt.volume,8),(long)vt.position_id);
   FileFlush(h);
   FileClose(h);
}

void LogOutcome(TrackedTrade &vt,string horizon,datetime utc_time)
{
   EnsureCommonFolder();
   int h = FileOpen(OutcomesFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h == INVALID_HANDLE) return;
   if(FileSize(h) == 0)
      FileWrite(h,"session_id","event_id","utc_text","symbol","side","horizon","mfe_r","mae_r","hit1_utc","hit2_utc","hit3_utc","hit4_utc","hit5_utc","stop_utc","ambiguous_same_m1");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session_id,vt.event_id,TimeToString(utc_time,TIME_DATE|TIME_SECONDS),_Symbol,SideName(vt.side),horizon,
             DoubleToString(vt.mfe_r,6),DoubleToString(vt.mae_r,6),(long)vt.hit1_utc,(long)vt.hit2_utc,(long)vt.hit3_utc,
             (long)vt.hit4_utc,(long)vt.hit5_utc,(long)vt.stop_utc,(vt.ambiguous ? "YES" : "NO"));
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

bool GetM15Stats(MqlRates &bar,MqlRates &prev,double &range_shock,double &relvol)
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M15,0,22,rates) < 22) return false;
   bar = rates[1];
   prev = rates[2];
   double mean_range = 0.0;
   double mean_volume = 0.0;
   for(int i=2;i<=21;i++)
   {
      mean_range += rates[i].high-rates[i].low;
      mean_volume += (double)rates[i].tick_volume;
   }
   mean_range /= 20.0;
   mean_volume /= 20.0;
   if(mean_range <= 0.0 || mean_volume <= 0.0) return false;
   range_shock = (bar.high-bar.low)/mean_range;
   relvol = (double)bar.tick_volume/mean_volume;
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
   tr.state=LER_IDLE; tr.bars_in_state=0; tr.event_id=""; tr.event_utc=0; tr.sweep_server_close=0; tr.sweep_utc=0;
   tr.frozen_level=0.0; tr.atr_h1=0.0; tr.sweep_extreme=0.0; tr.sweep_depth_atr=0.0; tr.cascade_range=0.0;
   tr.cascade_volume=0; tr.cascade_range_shock=0.0; tr.cascade_body_atr=0.0; tr.cascade_relvol=0.0;
   tr.last_outward_extreme=0.0; tr.reclaim_utc=0; tr.acceptance_closes=0; tr.validation_path="";
}

bool IsCascade(LerSide side,MqlRates &bar,double atr,double range_shock,double relvol,double &body_atr)
{
   if(atr<=0.0) return false;
   double directional_body = (side==SIDE_LONG ? bar.open-bar.close : bar.close-bar.open);
   body_atr = directional_body/atr;
   return (directional_body>0.0 && range_shock>=CASCADE_RANGE_SHOCK && body_atr>=CASCADE_BODY_ATR && relvol>=CASCADE_RELVOL);
}

void TransitionCascade(LevelTracker &tr,MqlRates &bar,double range_shock,double body_atr,double relvol,datetime utc_now)
{
   tr.state=LER_CASCADE; tr.bars_in_state=0; tr.cascade_range=bar.high-bar.low; tr.cascade_volume=(long)bar.tick_volume;
   tr.cascade_range_shock=range_shock; tr.cascade_body_atr=body_atr; tr.cascade_relvol=relvol;
   LerSide side=LevelSide(tr.level_index);
   if(side==SIDE_LONG) { tr.sweep_extreme=MathMin(tr.sweep_extreme,bar.low); tr.last_outward_extreme=tr.sweep_extreme; }
   else { tr.sweep_extreme=MathMax(tr.sweep_extreme,bar.high); tr.last_outward_extreme=tr.sweep_extreme; }
   LogEvent(tr,"CASCADE",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,body_atr,relvol,-1.0);
   if(InpVerbose) Print("[D025T][",_Symbol,"][",LevelName(tr.level_index),"] CASCADE event=",tr.event_id);
}

int FindFreeTradeSlot()
{
   for(int i=0;i<MAX_TRACKED_TRADES;i++) if(!g_trades[i].active) return i;
   return -1;
}

int VolumeDigits(double step)
{
   int d=0;
   while(d<8 && NormalizeDouble(step,d)!=step) d++;
   return d;
}

double NormalizeVolume(double volume)
{
   double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   volume=MathMin(vmax,MathMax(vmin,volume));
   volume=MathFloor(volume/step+1e-9)*step;
   if(volume<vmin) return 0.0;
   return NormalizeDouble(volume,VolumeDigits(step));
}

double CalcRiskVolume(LerSide side,double stop)
{
   double price=(side==SIDE_LONG ? SymbolInfoDouble(_Symbol,SYMBOL_ASK) : SymbolInfoDouble(_Symbol,SYMBOL_BID));
   if(price<=0.0 || stop<=0.0) return 0.0;
   if((side==SIDE_LONG && stop>=price) || (side==SIDE_SHORT && stop<=price)) return 0.0;
   double loss_one_lot=0.0;
   ENUM_ORDER_TYPE type=(side==SIDE_LONG ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,price,stop,loss_one_lot)) return 0.0;
   loss_one_lot=MathAbs(loss_one_lot);
   if(loss_one_lot<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*(InpRiskPercent/100.0);
   if(risk_cash<=0.0) return 0.0;
   return NormalizeVolume(risk_cash/loss_one_lot);
}

ulong PositionIdentifierFromResultDeal()
{
   ulong deal=g_trade.ResultDeal();
   if(deal==0 || !HistoryDealSelect(deal)) return 0;
   return (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
}

ulong FindPositionTicketByIdentifier(ulong identifier)
{
   if(identifier==0) return 0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER)==identifier) return ticket;
   }
   return 0;
}

bool OpenMarketTrade(LerSide side,double stop,string comment,double &volume,double &entry,ulong &position_id)
{
   volume=CalcRiskVolume(side,stop);
   entry=0.0; position_id=0;
   if(volume<=0.0)
   {
      Print("[D025T][ORDER_REJECT] volume calculation failed");
      return false;
   }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   bool ok=(side==SIDE_LONG ? g_trade.Buy(volume,_Symbol,0.0,stop,0.0,comment) : g_trade.Sell(volume,_Symbol,0.0,stop,0.0,comment));
   if(!ok)
   {
      Print("[D025T][ORDER_REJECT] ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
      return false;
   }
   entry=g_trade.ResultPrice();
   position_id=PositionIdentifierFromResultDeal();
   if(entry<=0.0) entry=(side==SIDE_LONG ? SymbolInfoDouble(_Symbol,SYMBOL_ASK) : SymbolInfoDouble(_Symbol,SYMBOL_BID));
   Print("[D025T][ORDER_OPEN] ",SideName(side)," ",_Symbol," vol=",DoubleToString(volume,8)," entry=",DoubleToString(entry,_Digits)," sl=",DoubleToString(stop,_Digits)," pos_id=",position_id);
   return true;
}

void CreateTrade(LevelTracker &tr,MqlRates &bar,string path,datetime utc_now)
{
   LerSide side=LevelSide(tr.level_index);
   double stop=(side==SIDE_LONG ? tr.sweep_extreme-STOP_BUFFER_ATR*tr.atr_h1 : tr.sweep_extreme+STOP_BUFFER_ATR*tr.atr_h1);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double signal_risk=MathAbs(bar.close-stop);
   if(signal_risk<=0.0 || point<=0.0 || signal_risk<5.0*point)
   {
      LogEvent(tr,"VALID_SIGNAL_REJECTED_BAD_RISK",utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1);
      ResetTracker(tr,true);
      return;
   }
   int slot=FindFreeTradeSlot();
   if(slot<0)
   {
      LogEvent(tr,"VALID_SIGNAL_REJECTED_NO_SLOT",utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1);
      ResetTracker(tr,true);
      return;
   }

   double volume=0.0,entry=0.0;
   ulong position_id=0;
   string comment=StringFormat("D025_%I64d",g_event_counter);
   tr.validation_path=path;
   LogEvent(tr,"VALID_SIGNAL_"+path,utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1);
   if(!OpenMarketTrade(side,stop,comment,volume,entry,position_id))
   {
      LogEvent(tr,"VALID_SIGNAL_ORDER_REJECTED",utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1);
      ResetTracker(tr,true);
      return;
   }

   TrackedTrade vt;
   vt.active=true; vt.event_id=tr.event_id; vt.side=side; vt.entry_utc=utc_now; vt.entry_server_time=bar.time+PeriodSeconds(PERIOD_M15);
   vt.entry=entry; vt.stop=stop; vt.risk=MathAbs(entry-stop); vt.volume=volume; vt.position_id=position_id;
   vt.mfe_r=0.0; vt.mae_r=0.0; vt.hit1_utc=0; vt.hit2_utc=0; vt.hit3_utc=0; vt.hit4_utc=0; vt.hit5_utc=0; vt.stop_utc=0;
   vt.ambiguous=false; vt.h1_logged=false; vt.h4_logged=false; vt.h8_logged=false; vt.h24_logged=false; vt.h48_logged=false;
   g_trades[slot]=vt;
   LogTrade(g_trades[slot],LevelName(tr.level_index),path);
   Print("[D025T][VALID_SIGNAL] event=",tr.event_id," side=",SideName(side)," level=",LevelName(tr.level_index)," path=",path);
   ResetTracker(tr,true);
}

void FailSequence(LevelTracker &tr,string reason,MqlRates &bar,datetime utc_now)
{
   LogEvent(tr,"FAILED_"+reason,utc_now,bar.time+PeriodSeconds(PERIOD_M15),-1,-1,-1,-1);
   if(InpVerbose) Print("[D025T][",_Symbol,"][",LevelName(tr.level_index),"] failed=",reason," event=",tr.event_id);
   ResetTracker(tr,true);
}

void ProcessTracker(LevelTracker &tr,MqlRates &bar,MqlRates &prev,double atr,double range_shock,double relvol,datetime utc_now)
{
   LerSide side=LevelSide(tr.level_index);
   if(tr.state==LER_IDLE || tr.state==LER_WATCH)
   {
      if(utc_now<tr.cooldown_until_utc) return;
      double live_level=0.0;
      if(!GetLevelPrice(tr.level_index,live_level) || live_level<=0.0) return;
      tr.level_price=live_level;
      double dist=MathAbs(bar.close-live_level);
      if(tr.state==LER_IDLE && dist<=WATCH_ATR*atr)
      {
         tr.state=LER_WATCH; tr.frozen_level=live_level; tr.atr_h1=atr; tr.event_id="";
         LogEvent(tr,"LEVEL_WATCH",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,-1.0,relvol,-1.0);
      }
      else if(tr.state==LER_WATCH && dist>2.0*WATCH_ATR*atr)
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

      tr.state=LER_SWEEP; tr.bars_in_state=0; tr.frozen_level=live_level; tr.atr_h1=atr; tr.sweep_depth_atr=depth;
      tr.sweep_utc=utc_now; tr.event_utc=utc_now; tr.sweep_server_close=bar.time+PeriodSeconds(PERIOD_M15);
      tr.sweep_extreme=(side==SIDE_LONG ? bar.low : bar.high); tr.last_outward_extreme=tr.sweep_extreme;
      g_event_counter++;
      tr.event_id=StringFormat("D025_%s_%s_%I64d_%I64d",_Symbol,LevelName(tr.level_index),(long)utc_now,g_event_counter);
      LogEvent(tr,"SWEEP",utc_now,tr.sweep_server_close,range_shock,-1.0,relvol,-1.0);
      if(InpVerbose) Print("[D025T][",_Symbol,"][",LevelName(tr.level_index),"] SWEEP event=",tr.event_id," depthATR=",DoubleToString(depth,3));
      double body_atr=0.0;
      if(IsCascade(side,bar,atr,range_shock,relvol,body_atr)) TransitionCascade(tr,bar,range_shock,body_atr,relvol,utc_now);
      return;
   }

   if(side==SIDE_LONG) tr.sweep_extreme=MathMin(tr.sweep_extreme,bar.low);
   else tr.sweep_extreme=MathMax(tr.sweep_extreme,bar.high);
   tr.bars_in_state++;

   if(tr.state==LER_SWEEP)
   {
      double body_atr=0.0;
      if(IsCascade(side,bar,atr,range_shock,relvol,body_atr)) { TransitionCascade(tr,bar,range_shock,body_atr,relvol,utc_now); return; }
      if(tr.bars_in_state>2) FailSequence(tr,"NO_CASCADE_2BARS",bar,utc_now);
      return;
   }

   if(tr.state==LER_CASCADE)
   {
      double progress=0.0;
      if(side==SIDE_LONG && bar.low<tr.last_outward_extreme) progress=tr.last_outward_extreme-bar.low;
      if(side==SIDE_SHORT && bar.high>tr.last_outward_extreme) progress=bar.high-tr.last_outward_extreme;
      double progress_frac=(tr.cascade_range>0.0 ? progress/tr.cascade_range : 999.0);
      bool activity_ok=((double)bar.tick_volume>=EXHAUST_ACTIVITY_FRAC*(double)tr.cascade_volume);
      if(progress_frac<=EXHAUST_PROGRESS_FRAC && activity_ok)
      {
         tr.state=LER_EXHAUSTION; tr.bars_in_state=0;
         if(side==SIDE_LONG) tr.last_outward_extreme=MathMin(tr.last_outward_extreme,bar.low); else tr.last_outward_extreme=MathMax(tr.last_outward_extreme,bar.high);
         LogEvent(tr,"EXHAUSTION",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,-1.0,relvol,progress_frac);
         if(InpVerbose) Print("[D025T][",_Symbol,"][",LevelName(tr.level_index),"] EXHAUSTION event=",tr.event_id);
         return;
      }
      if(side==SIDE_LONG) tr.last_outward_extreme=MathMin(tr.last_outward_extreme,bar.low); else tr.last_outward_extreme=MathMax(tr.last_outward_extreme,bar.high);
      if(tr.bars_in_state>3) FailSequence(tr,"NO_EXHAUSTION_3BARS",bar,utc_now);
      return;
   }

   if(tr.state==LER_EXHAUSTION)
   {
      bool reclaimed=(side==SIDE_LONG ? bar.close>tr.frozen_level : bar.close<tr.frozen_level);
      if(reclaimed)
      {
         tr.state=LER_RECLAIM; tr.bars_in_state=0; tr.reclaim_utc=utc_now; tr.acceptance_closes=1;
         LogEvent(tr,"RECLAIM",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,-1.0,relvol,-1.0);
         return;
      }
      if(tr.bars_in_state>4) FailSequence(tr,"NO_RECLAIM_4BARS",bar,utc_now);
      return;
   }

   if(tr.state==LER_RECLAIM)
   {
      bool inside_close=(side==SIDE_LONG ? bar.close>tr.frozen_level : bar.close<tr.frozen_level);
      bool retest=(side==SIDE_LONG ? (bar.low<=tr.frozen_level+RETEST_ATR*tr.atr_h1 && bar.close>tr.frozen_level)
                                  : (bar.high>=tr.frozen_level-RETEST_ATR*tr.atr_h1 && bar.close<tr.frozen_level));
      if(retest) { CreateTrade(tr,bar,"RETEST",utc_now); return; }
      if(inside_close) tr.acceptance_closes++; else tr.acceptance_closes=0;
      if(tr.acceptance_closes>=2) { CreateTrade(tr,bar,"ACCEPTANCE",utc_now); return; }
      if(tr.bars_in_state>4) FailSequence(tr,"NO_RETEST_ACCEPTANCE_4BARS",bar,utc_now);
   }
}

void ProcessM15()
{
   datetime closed_open=iTime(_Symbol,PERIOD_M15,1);
   if(closed_open<=0 || closed_open==g_last_m15_closed_open) return;
   MqlRates bar,prev; double range_shock=0.0,relvol=0.0;
   if(!GetM15Stats(bar,prev,range_shock,relvol)) { LogReview("insufficient M15 history"); return; }
   double atr=0.0;
   if(!GetAtrH1(atr)) { LogReview("H1 ATR unavailable"); return; }
   g_last_m15_closed_open=closed_open;
   datetime utc_now=TimeGMT();
   for(int i=0;i<LEVEL_COUNT;i++) ProcessTracker(g_trackers[i],bar,prev,atr,range_shock,relvol,utc_now);
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
   if(r==1) return vt.hit1_utc!=0; if(r==2) return vt.hit2_utc!=0; if(r==3) return vt.hit3_utc!=0;
   if(r==4) return vt.hit4_utc!=0; if(r==5) return vt.hit5_utc!=0; return true;
}

void CloseAtTimeLimit(TrackedTrade &vt)
{
   ulong ticket=FindPositionTicketByIdentifier(vt.position_id);
   if(ticket==0) return;
   g_trade.SetExpertMagicNumber(InpMagic);
   if(g_trade.PositionClose(ticket))
      Print("[D025T][TIME_EXIT] event=",vt.event_id," ticket=",ticket," after ",InpMaxHoldHours,"h");
   else
      Print("[D025T][TIME_EXIT_FAIL] event=",vt.event_id," ",g_trade.ResultRetcodeDescription());
}

void ProcessTradeBar(TrackedTrade &vt,MqlRates &bar,datetime utc_now)
{
   datetime bar_close_server=bar.time+PeriodSeconds(PERIOD_M1);
   if(bar_close_server<=vt.entry_server_time || vt.risk<=0.0) return;
   double fav=0.0,adv=0.0;
   if(vt.side==SIDE_LONG) { fav=MathMax(0.0,bar.high-vt.entry)/vt.risk; adv=MathMax(0.0,vt.entry-bar.low)/vt.risk; }
   else { fav=MathMax(0.0,vt.entry-bar.low)/vt.risk; adv=MathMax(0.0,bar.high-vt.entry)/vt.risk; }
   vt.mfe_r=MathMax(vt.mfe_r,fav); vt.mae_r=MathMax(vt.mae_r,adv);

   bool stop_cross=false;
   if(vt.stop_utc==0) stop_cross=(vt.side==SIDE_LONG ? bar.low<=vt.stop : bar.high>=vt.stop);
   bool new_positive_hit=false;
   for(int r=1;r<=5;r++)
   {
      if(AlreadyHit(vt,r)) continue;
      double target=(vt.side==SIDE_LONG ? vt.entry+r*vt.risk : vt.entry-r*vt.risk);
      bool crossed=(vt.side==SIDE_LONG ? bar.high>=target : bar.low<=target);
      if(crossed) { SetHitIfNeeded(vt,r,utc_now); new_positive_hit=true; }
   }
   if(stop_cross)
   {
      vt.stop_utc=utc_now;
      if(new_positive_hit) { vt.ambiguous=true; Print("[D025T][AMBIGUOUS_M1] event=",vt.event_id); }
   }

   long elapsed=(long)(utc_now-vt.entry_utc);
   if(!vt.h1_logged && elapsed>=3600) { vt.h1_logged=true; LogOutcome(vt,"1H",utc_now); }
   if(!vt.h4_logged && elapsed>=4*3600) { vt.h4_logged=true; LogOutcome(vt,"4H",utc_now); }
   if(!vt.h8_logged && elapsed>=8*3600) { vt.h8_logged=true; LogOutcome(vt,"8H",utc_now); }
   if(!vt.h24_logged && elapsed>=24*3600) { vt.h24_logged=true; LogOutcome(vt,"24H",utc_now); }
   if(!vt.h48_logged && elapsed>=InpMaxHoldHours*3600)
   {
      CloseAtTimeLimit(vt);
      vt.h48_logged=true;
      LogOutcome(vt,StringFormat("%dH",InpMaxHoldHours),utc_now);
      Print("[D025T][COMPLETE] event=",vt.event_id," MFE=",DoubleToString(vt.mfe_r,2),"R MAE=",DoubleToString(vt.mae_r,2),"R");
      vt.active=false;
   }
}

void ProcessM1()
{
   datetime closed_open=iTime(_Symbol,PERIOD_M1,1);
   if(closed_open<=0 || closed_open==g_last_m1_closed_open) return;
   MqlRates rates[]; ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M1,0,2,rates)<2) return;
   g_last_m1_closed_open=closed_open;
   datetime utc_now=TimeGMT();
   for(int i=0;i<MAX_TRACKED_TRADES;i++) if(g_trades[i].active) ProcessTradeBar(g_trades[i],rates[1],utc_now);
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>100.0 || InpMaxHoldHours<=0) return INIT_PARAMETERS_INCORRECT;
   if(!SymbolSelect(_Symbol,true)) return INIT_FAILED;
   g_atr_h1_handle=iATR(_Symbol,PERIOD_H1,14);
   if(g_atr_h1_handle==INVALID_HANDLE)
   {
      Print("[D025T][FATAL] cannot create H1 ATR handle for ",_Symbol," error=",GetLastError());
      return INIT_FAILED;
   }
   g_session_id=StringFormat("D025T_%s_%I64d_%I64d",_Symbol,(long)TimeGMT(),(long)GetTickCount64());
   for(int i=0;i<LEVEL_COUNT;i++)
   {
      g_trackers[i].level_index=i;
      g_trackers[i].cooldown_until_utc=0;
      ResetTracker(g_trackers[i],false);
   }
   for(int i=0;i<MAX_TRACKED_TRADES;i++) g_trades[i].active=false;
   EnsureCommonFolder();
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   EventSetTimer(MathMax(1,InpTimerSeconds));
   Print("[D025T][START] Trading 1.01 symbol=",_Symbol," risk=",DoubleToString(InpRiskPercent,2),"% max_hold=",InpMaxHoldHours,"h | SL_STRUCTURAL | NO_TP");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_atr_h1_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_h1_handle);
   Print("[D025T][STOP] reason=",reason);
}

void OnTimer()
{
   ProcessM15();
   ProcessM1();
}

void OnTick()
{
   // Keep timer-driven closed-bar logic identical in spirit to the V0 observer.
}
