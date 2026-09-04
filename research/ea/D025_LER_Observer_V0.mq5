#property strict
#property version   "0.100"
#property description "D025 LER V0 research observer - NO LIVE ORDERS"

// D025 Liquidity Exhaustion Reclaim V0
// Research-only observer. It contains NO trading library and NO order function.
// Rules are locked in research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md

input string InpSymbol1 = "BTCUSD";
input string InpSymbol2 = "ETHUSD";
input int    InpTimerSeconds = 1;
input bool   InpVerbose = true;

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

#define SYMBOL_COUNT 2
#define LEVEL_COUNT 8
#define MAX_TRACKERS (SYMBOL_COUNT*LEVEL_COUNT)
#define MAX_VIRTUAL_TRADES 64

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

struct SymbolContext
{
   string symbol;
   int atr_h1_handle;
   datetime last_m15_closed_open;
   datetime last_m1_closed_open;
   bool ready;
};

struct LevelTracker
{
   int symbol_index;
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

struct VirtualTrade
{
   bool active;
   string event_id;
   string symbol;
   LerSide side;
   datetime entry_utc;
   datetime entry_server_time;
   double entry;
   double stop;
   double risk;
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

SymbolContext g_symbols[SYMBOL_COUNT];
LevelTracker g_trackers[MAX_TRACKERS];
VirtualTrade g_trades[MAX_VIRTUAL_TRADES];
long g_event_counter = 0;
string g_session_id = "";
datetime g_last_review_log_utc = 0;

string StateName(LerState s)
{
   if(s == LER_IDLE) return "IDLE";
   if(s == LER_WATCH) return "LEVEL_WATCH";
   if(s == LER_SWEEP) return "SWEEP";
   if(s == LER_CASCADE) return "CASCADE";
   if(s == LER_EXHAUSTION) return "EXHAUSTION";
   if(s == LER_RECLAIM) return "RECLAIM";
   return "UNKNOWN";
}

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

int TrackerIndex(int symbol_index, int level_index)
{
   return symbol_index * LEVEL_COUNT + level_index;
}

void EnsureCommonFolder()
{
   FolderCreate("GuardianResearch", FILE_COMMON);
   FolderCreate("GuardianResearch\\D025", FILE_COMMON);
}

string EventsFile()
{
   return "GuardianResearch\\D025\\d025_ler_v0_events.csv";
}

string TradesFile()
{
   return "GuardianResearch\\D025\\d025_ler_v0_virtual_trades.csv";
}

string OutcomesFile()
{
   return "GuardianResearch\\D025\\d025_ler_v0_outcomes.csv";
}

void LogReview(string msg)
{
   datetime now = TimeGMT();
   if(now - g_last_review_log_utc < 60)
      return;
   g_last_review_log_utc = now;
   Print("[D025][REVIEW] ", msg);
}

void LogEvent(LevelTracker &tr, string transition, datetime utc_time, datetime server_bar_close,
              double range_shock, double body_atr, double relvol, double extra_progress_frac)
{
   EnsureCommonFolder();
   int h = FileOpen(EventsFile(), FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE, ';');
   if(h == INVALID_HANDLE)
   {
      Print("[D025][REVIEW] cannot open events CSV error=", GetLastError());
      return;
   }
   if(FileSize(h) == 0)
   {
      FileWrite(h,
         "session_id","event_id","utc_epoch","utc_text","server_bar_close","symbol","level_family","side","transition",
         "level_price","atr_h1","sweep_depth_atr","range_shock","body_atr","rel_tick_volume","extra_progress_frac",
         "sweep_extreme","time_outside_sec","time_to_reclaim_sec","validation_path");
   }
   FileSeek(h, 0, SEEK_END);
   int sidx = tr.symbol_index;
   long outside_sec = (tr.sweep_utc > 0 ? (long)(utc_time - tr.sweep_utc) : 0);
   long reclaim_sec = (tr.reclaim_utc > 0 && tr.sweep_utc > 0 ? (long)(tr.reclaim_utc - tr.sweep_utc) : 0);
   FileWrite(h,
      g_session_id,
      tr.event_id,
      (long)utc_time,
      TimeToString(utc_time, TIME_DATE|TIME_SECONDS),
      TimeToString(server_bar_close, TIME_DATE|TIME_SECONDS),
      g_symbols[sidx].symbol,
      LevelName(tr.level_index),
      SideName(LevelSide(tr.level_index)),
      transition,
      DoubleToString(tr.frozen_level, (int)SymbolInfoInteger(g_symbols[sidx].symbol, SYMBOL_DIGITS)),
      DoubleToString(tr.atr_h1, 8),
      DoubleToString(tr.sweep_depth_atr, 6),
      DoubleToString(range_shock, 6),
      DoubleToString(body_atr, 6),
      DoubleToString(relvol, 6),
      DoubleToString(extra_progress_frac, 6),
      DoubleToString(tr.sweep_extreme, (int)SymbolInfoInteger(g_symbols[sidx].symbol, SYMBOL_DIGITS)),
      outside_sec,
      reclaim_sec,
      tr.validation_path);
   FileFlush(h);
   FileClose(h);
}

void LogVirtualTrade(VirtualTrade &vt, string level_family, double atr_h1, double level_price)
{
   EnsureCommonFolder();
   int h = FileOpen(TradesFile(), FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE, ';');
   if(h == INVALID_HANDLE)
   {
      Print("[D025][REVIEW] cannot open trades CSV error=", GetLastError());
      return;
   }
   if(FileSize(h) == 0)
   {
      FileWrite(h,"session_id","event_id","entry_utc_epoch","entry_utc_text","symbol","side","level_family","level_price","atr_h1","entry","virtual_sl","risk","status");
   }
   FileSeek(h, 0, SEEK_END);
   int digits = (int)SymbolInfoInteger(vt.symbol, SYMBOL_DIGITS);
   FileWrite(h,
      g_session_id, vt.event_id, (long)vt.entry_utc, TimeToString(vt.entry_utc,TIME_DATE|TIME_SECONDS), vt.symbol,
      SideName(vt.side), level_family, DoubleToString(level_price,digits), DoubleToString(atr_h1,8),
      DoubleToString(vt.entry,digits), DoubleToString(vt.stop,digits), DoubleToString(vt.risk,digits), "OPEN_VIRTUAL_48H_OBSERVATION");
   FileFlush(h);
   FileClose(h);
}

void LogOutcome(VirtualTrade &vt, string horizon, datetime utc_time)
{
   EnsureCommonFolder();
   int h = FileOpen(OutcomesFile(), FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE, ';');
   if(h == INVALID_HANDLE)
   {
      Print("[D025][REVIEW] cannot open outcomes CSV error=", GetLastError());
      return;
   }
   if(FileSize(h) == 0)
   {
      FileWrite(h,"session_id","event_id","utc_epoch","utc_text","symbol","side","horizon","mfe_r","mae_r",
                   "hit1_utc","hit2_utc","hit3_utc","hit4_utc","hit5_utc","stop_utc","ambiguous_same_m1");
   }
   FileSeek(h, 0, SEEK_END);
   FileWrite(h,
      g_session_id, vt.event_id, (long)utc_time, TimeToString(utc_time,TIME_DATE|TIME_SECONDS), vt.symbol, SideName(vt.side), horizon,
      DoubleToString(vt.mfe_r,6), DoubleToString(vt.mae_r,6),
      (long)vt.hit1_utc,(long)vt.hit2_utc,(long)vt.hit3_utc,(long)vt.hit4_utc,(long)vt.hit5_utc,(long)vt.stop_utc,
      (vt.ambiguous ? "YES" : "NO"));
   FileFlush(h);
   FileClose(h);
}

bool GetAtrH1(int symbol_index, double &atr)
{
   atr = 0.0;
   if(g_symbols[symbol_index].atr_h1_handle == INVALID_HANDLE)
      return false;
   double buf[1];
   if(CopyBuffer(g_symbols[symbol_index].atr_h1_handle, 0, 1, 1, buf) != 1)
      return false;
   atr = buf[0];
   return (atr > 0.0);
}

bool GetM15Stats(string sym, MqlRates &bar, MqlRates &prev, double &mean_range, double &mean_volume,
                 double &range_shock, double &relvol)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(sym, PERIOD_M15, 0, 22, rates);
   if(copied < 22)
      return false;
   bar = rates[1];
   prev = rates[2];
   mean_range = 0.0;
   mean_volume = 0.0;
   for(int i=2; i<=21; i++)
   {
      mean_range += (rates[i].high - rates[i].low);
      mean_volume += (double)rates[i].tick_volume;
   }
   mean_range /= 20.0;
   mean_volume /= 20.0;
   if(mean_range <= 0.0 || mean_volume <= 0.0)
      return false;
   range_shock = (bar.high - bar.low) / mean_range;
   relvol = (double)bar.tick_volume / mean_volume;
   return true;
}

bool FindLatestSwing(string sym, ENUM_TIMEFRAMES tf, bool want_high, double &price)
{
   price = 0.0;
   int bars = Bars(sym, tf);
   if(bars < 20)
      return false;
   int max_shift = MathMin(120, bars - 3);
   for(int s=3; s<=max_shift; s++)
   {
      double p = (want_high ? iHigh(sym,tf,s) : iLow(sym,tf,s));
      if(p <= 0.0) continue;
      bool pivot = false;
      if(want_high)
      {
         pivot = (p > iHigh(sym,tf,s-1) && p > iHigh(sym,tf,s-2) && p > iHigh(sym,tf,s+1) && p > iHigh(sym,tf,s+2));
      }
      else
      {
         pivot = (p < iLow(sym,tf,s-1) && p < iLow(sym,tf,s-2) && p < iLow(sym,tf,s+1) && p < iLow(sym,tf,s+2));
      }
      if(pivot)
      {
         price = p;
         return true;
      }
   }
   return false;
}

bool GetLevelPrice(string sym, int level_index, double &price)
{
   price = 0.0;
   switch(level_index)
   {
      case 0: price = iHigh(sym, PERIOD_D1, 1); return (price > 0.0);
      case 1: price = iLow(sym, PERIOD_D1, 1); return (price > 0.0);
      case 2: price = iHigh(sym, PERIOD_W1, 1); return (price > 0.0);
      case 3: price = iLow(sym, PERIOD_W1, 1); return (price > 0.0);
      case 4: return FindLatestSwing(sym, PERIOD_H1, true, price);
      case 5: return FindLatestSwing(sym, PERIOD_H1, false, price);
      case 6: return FindLatestSwing(sym, PERIOD_H4, true, price);
      case 7: return FindLatestSwing(sym, PERIOD_H4, false, price);
   }
   return false;
}

void ResetTracker(LevelTracker &tr, bool apply_cooldown)
{
   if(apply_cooldown)
      tr.cooldown_until_utc = TimeGMT() + COOLDOWN_SECONDS;
   tr.state = LER_IDLE;
   tr.bars_in_state = 0;
   tr.event_id = "";
   tr.event_utc = 0;
   tr.sweep_server_close = 0;
   tr.sweep_utc = 0;
   tr.frozen_level = 0.0;
   tr.atr_h1 = 0.0;
   tr.sweep_extreme = 0.0;
   tr.sweep_depth_atr = 0.0;
   tr.cascade_range = 0.0;
   tr.cascade_volume = 0;
   tr.cascade_range_shock = 0.0;
   tr.cascade_body_atr = 0.0;
   tr.cascade_relvol = 0.0;
   tr.last_outward_extreme = 0.0;
   tr.reclaim_utc = 0;
   tr.acceptance_closes = 0;
   tr.validation_path = "";
}

bool IsCascade(LerSide side, MqlRates &bar, double atr, double range_shock, double relvol, double &body_atr)
{
   if(atr <= 0.0) return false;
   double directional_body = 0.0;
   if(side == SIDE_LONG)
      directional_body = bar.open - bar.close;
   else
      directional_body = bar.close - bar.open;
   body_atr = directional_body / atr;
   return (directional_body > 0.0 && range_shock >= CASCADE_RANGE_SHOCK && body_atr >= CASCADE_BODY_ATR && relvol >= CASCADE_RELVOL);
}

void TransitionCascade(LevelTracker &tr, MqlRates &bar, double range_shock, double body_atr, double relvol, datetime utc_now)
{
   tr.state = LER_CASCADE;
   tr.bars_in_state = 0;
   tr.cascade_range = bar.high - bar.low;
   tr.cascade_volume = (long)bar.tick_volume;
   tr.cascade_range_shock = range_shock;
   tr.cascade_body_atr = body_atr;
   tr.cascade_relvol = relvol;
   LerSide side = LevelSide(tr.level_index);
   if(side == SIDE_LONG)
   {
      tr.sweep_extreme = MathMin(tr.sweep_extreme, bar.low);
      tr.last_outward_extreme = tr.sweep_extreme;
   }
   else
   {
      tr.sweep_extreme = MathMax(tr.sweep_extreme, bar.high);
      tr.last_outward_extreme = tr.sweep_extreme;
   }
   LogEvent(tr, "CASCADE", utc_now, bar.time + PeriodSeconds(PERIOD_M15), range_shock, body_atr, relvol, -1.0);
   if(InpVerbose) Print("[D025][",g_symbols[tr.symbol_index].symbol,"][",LevelName(tr.level_index),"] CASCADE event=",tr.event_id);
}

int FindFreeTradeSlot()
{
   for(int i=0;i<MAX_VIRTUAL_TRADES;i++)
      if(!g_trades[i].active) return i;
   return -1;
}

void CreateVirtualTrade(LevelTracker &tr, MqlRates &bar, string path, datetime utc_now)
{
   string sym = g_symbols[tr.symbol_index].symbol;
   LerSide side = LevelSide(tr.level_index);
   double entry = bar.close;
   double stop = (side == SIDE_LONG ? tr.sweep_extreme - STOP_BUFFER_ATR*tr.atr_h1 : tr.sweep_extreme + STOP_BUFFER_ATR*tr.atr_h1);
   double risk = MathAbs(entry - stop);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   if(risk <= 0.0 || point <= 0.0 || risk < 5.0*point)
   {
      Print("[D025][REVIEW] invalid virtual risk event=",tr.event_id," risk=",DoubleToString(risk,8));
      LogEvent(tr, "VALID_SIGNAL_REJECTED_BAD_RISK", utc_now, bar.time + PeriodSeconds(PERIOD_M15), -1,-1,-1,-1);
      ResetTracker(tr, true);
      return;
   }

   int slot = FindFreeTradeSlot();
   if(slot < 0)
   {
      Print("[D025][REVIEW] virtual trade slots full; event=",tr.event_id);
      LogEvent(tr, "VALID_SIGNAL_REJECTED_NO_SLOT", utc_now, bar.time + PeriodSeconds(PERIOD_M15), -1,-1,-1,-1);
      ResetTracker(tr, true);
      return;
   }

   VirtualTrade vt;
   vt.active = true;
   vt.event_id = tr.event_id;
   vt.symbol = sym;
   vt.side = side;
   vt.entry_utc = utc_now;
   vt.entry_server_time = bar.time + PeriodSeconds(PERIOD_M15);
   vt.entry = entry;
   vt.stop = stop;
   vt.risk = risk;
   vt.mfe_r = 0.0;
   vt.mae_r = 0.0;
   vt.hit1_utc = 0; vt.hit2_utc = 0; vt.hit3_utc = 0; vt.hit4_utc = 0; vt.hit5_utc = 0;
   vt.stop_utc = 0;
   vt.ambiguous = false;
   vt.h1_logged = false; vt.h4_logged = false; vt.h8_logged = false; vt.h24_logged = false; vt.h48_logged = false;
   g_trades[slot] = vt;

   tr.validation_path = path;
   LogEvent(tr, "VALID_SIGNAL_"+path, utc_now, vt.entry_server_time, -1,-1,-1,-1);
   LogVirtualTrade(g_trades[slot], LevelName(tr.level_index), tr.atr_h1, tr.frozen_level);
   Print("[D025][VALID_SIGNAL][",sym,"] event=",tr.event_id," side=",SideName(side)," level=",LevelName(tr.level_index)," path=",path," entry=",DoubleToString(entry,(int)SymbolInfoInteger(sym,SYMBOL_DIGITS))," risk=",DoubleToString(risk,(int)SymbolInfoInteger(sym,SYMBOL_DIGITS))," | VIRTUAL_ONLY_NO_ORDER");
   ResetTracker(tr, true);
}

void FailSequence(LevelTracker &tr, string reason, MqlRates &bar, datetime utc_now)
{
   LogEvent(tr, "FAILED_"+reason, utc_now, bar.time + PeriodSeconds(PERIOD_M15), -1,-1,-1,-1);
   if(InpVerbose) Print("[D025][",g_symbols[tr.symbol_index].symbol,"][",LevelName(tr.level_index),"] failed=",reason," event=",tr.event_id);
   ResetTracker(tr, true);
}

void ProcessTracker(LevelTracker &tr, MqlRates &bar, MqlRates &prev, double atr, double range_shock, double relvol, datetime utc_now)
{
   string sym = g_symbols[tr.symbol_index].symbol;
   LerSide side = LevelSide(tr.level_index);

   if(tr.state == LER_IDLE || tr.state == LER_WATCH)
   {
      if(utc_now < tr.cooldown_until_utc)
         return;

      double live_level = 0.0;
      if(!GetLevelPrice(sym, tr.level_index, live_level) || live_level <= 0.0)
         return;
      tr.level_price = live_level;

      double dist = MathAbs(bar.close - live_level);
      if(tr.state == LER_IDLE && dist <= WATCH_ATR*atr)
      {
         tr.state = LER_WATCH;
         tr.frozen_level = live_level;
         tr.atr_h1 = atr;
         tr.event_id = "";
         LogEvent(tr, "LEVEL_WATCH", utc_now, bar.time + PeriodSeconds(PERIOD_M15), range_shock, -1.0, relvol, -1.0);
      }
      else if(tr.state == LER_WATCH && dist > 2.0*WATCH_ATR*atr)
      {
         ResetTracker(tr, false);
         return;
      }

      bool fresh_sweep = false;
      double depth = 0.0;
      if(side == SIDE_LONG)
      {
         fresh_sweep = (prev.close >= live_level && bar.low <= live_level - SWEEP_MIN_ATR*atr);
         if(fresh_sweep) depth = (live_level - bar.low) / atr;
      }
      else
      {
         fresh_sweep = (prev.close <= live_level && bar.high >= live_level + SWEEP_MIN_ATR*atr);
         if(fresh_sweep) depth = (bar.high - live_level) / atr;
      }

      if(!fresh_sweep)
         return;

      tr.state = LER_SWEEP;
      tr.bars_in_state = 0;
      tr.frozen_level = live_level;
      tr.atr_h1 = atr;
      tr.sweep_depth_atr = depth;
      tr.sweep_utc = utc_now;
      tr.event_utc = utc_now;
      tr.sweep_server_close = bar.time + PeriodSeconds(PERIOD_M15);
      tr.sweep_extreme = (side == SIDE_LONG ? bar.low : bar.high);
      tr.last_outward_extreme = tr.sweep_extreme;
      g_event_counter++;
      tr.event_id = StringFormat("D025_%s_%s_%I64d_%I64d", sym, LevelName(tr.level_index), (long)utc_now, g_event_counter);
      LogEvent(tr, "SWEEP", utc_now, tr.sweep_server_close, range_shock, -1.0, relvol, -1.0);
      if(InpVerbose) Print("[D025][",sym,"][",LevelName(tr.level_index),"] SWEEP event=",tr.event_id," depthATR=",DoubleToString(depth,3));

      double body_atr = 0.0;
      if(IsCascade(side, bar, atr, range_shock, relvol, body_atr))
         TransitionCascade(tr, bar, range_shock, body_atr, relvol, utc_now);
      return;
   }

   // Keep the most adverse extreme through the sequence.
   if(side == SIDE_LONG)
      tr.sweep_extreme = MathMin(tr.sweep_extreme, bar.low);
   else
      tr.sweep_extreme = MathMax(tr.sweep_extreme, bar.high);

   tr.bars_in_state++;

   if(tr.state == LER_SWEEP)
   {
      double body_atr = 0.0;
      if(IsCascade(side, bar, atr, range_shock, relvol, body_atr))
      {
         TransitionCascade(tr, bar, range_shock, body_atr, relvol, utc_now);
         return;
      }
      if(tr.bars_in_state > 2)
         FailSequence(tr, "NO_CASCADE_2BARS", bar, utc_now);
      return;
   }

   if(tr.state == LER_CASCADE)
   {
      double progress = 0.0;
      if(side == SIDE_LONG)
      {
         if(bar.low < tr.last_outward_extreme)
            progress = tr.last_outward_extreme - bar.low;
      }
      else
      {
         if(bar.high > tr.last_outward_extreme)
            progress = bar.high - tr.last_outward_extreme;
      }
      double progress_frac = (tr.cascade_range > 0.0 ? progress / tr.cascade_range : 999.0);
      bool activity_ok = ((double)bar.tick_volume >= EXHAUST_ACTIVITY_FRAC*(double)tr.cascade_volume);
      if(progress_frac <= EXHAUST_PROGRESS_FRAC && activity_ok)
      {
         tr.state = LER_EXHAUSTION;
         tr.bars_in_state = 0;
         if(side == SIDE_LONG) tr.last_outward_extreme = MathMin(tr.last_outward_extreme, bar.low);
         else tr.last_outward_extreme = MathMax(tr.last_outward_extreme, bar.high);
         LogEvent(tr, "EXHAUSTION", utc_now, bar.time + PeriodSeconds(PERIOD_M15), range_shock, -1.0, relvol, progress_frac);
         if(InpVerbose) Print("[D025][",sym,"][",LevelName(tr.level_index),"] EXHAUSTION event=",tr.event_id," progressFrac=",DoubleToString(progress_frac,3));
         return;
      }
      if(side == SIDE_LONG) tr.last_outward_extreme = MathMin(tr.last_outward_extreme, bar.low);
      else tr.last_outward_extreme = MathMax(tr.last_outward_extreme, bar.high);
      if(tr.bars_in_state > 3)
         FailSequence(tr, "NO_EXHAUSTION_3BARS", bar, utc_now);
      return;
   }

   if(tr.state == LER_EXHAUSTION)
   {
      bool reclaimed = (side == SIDE_LONG ? bar.close > tr.frozen_level : bar.close < tr.frozen_level);
      if(reclaimed)
      {
         tr.state = LER_RECLAIM;
         tr.bars_in_state = 0;
         tr.reclaim_utc = utc_now;
         tr.acceptance_closes = 1;
         LogEvent(tr, "RECLAIM", utc_now, bar.time + PeriodSeconds(PERIOD_M15), range_shock, -1.0, relvol, -1.0);
         if(InpVerbose) Print("[D025][",sym,"][",LevelName(tr.level_index),"] RECLAIM event=",tr.event_id);
         return;
      }
      if(tr.bars_in_state > 4)
         FailSequence(tr, "NO_RECLAIM_4BARS", bar, utc_now);
      return;
   }

   if(tr.state == LER_RECLAIM)
   {
      bool inside_close = (side == SIDE_LONG ? bar.close > tr.frozen_level : bar.close < tr.frozen_level);
      bool retest = false;
      if(side == SIDE_LONG)
         retest = (bar.low <= tr.frozen_level + RETEST_ATR*tr.atr_h1 && bar.close > tr.frozen_level);
      else
         retest = (bar.high >= tr.frozen_level - RETEST_ATR*tr.atr_h1 && bar.close < tr.frozen_level);

      if(retest)
      {
         CreateVirtualTrade(tr, bar, "RETEST", utc_now);
         return;
      }

      if(inside_close) tr.acceptance_closes++;
      else tr.acceptance_closes = 0;

      if(tr.acceptance_closes >= 2)
      {
         CreateVirtualTrade(tr, bar, "ACCEPTANCE", utc_now);
         return;
      }

      if(tr.bars_in_state > 4)
         FailSequence(tr, "NO_RETEST_ACCEPTANCE_4BARS", bar, utc_now);
      return;
   }
}

void ProcessM15Symbol(int symbol_index)
{
   string sym = g_symbols[symbol_index].symbol;
   datetime closed_open = iTime(sym, PERIOD_M15, 1);
   if(closed_open <= 0 || closed_open == g_symbols[symbol_index].last_m15_closed_open)
      return;

   MqlRates bar, prev;
   double mean_range=0.0, mean_volume=0.0, range_shock=0.0, relvol=0.0;
   if(!GetM15Stats(sym, bar, prev, mean_range, mean_volume, range_shock, relvol))
   {
      LogReview(sym+" insufficient M15 history");
      return;
   }

   double atr=0.0;
   if(!GetAtrH1(symbol_index, atr))
   {
      LogReview(sym+" H1 ATR unavailable");
      return;
   }

   g_symbols[symbol_index].last_m15_closed_open = closed_open;
   datetime utc_now = TimeGMT();
   for(int lvl=0; lvl<LEVEL_COUNT; lvl++)
   {
      int idx = TrackerIndex(symbol_index,lvl);
      ProcessTracker(g_trackers[idx], bar, prev, atr, range_shock, relvol, utc_now);
   }
}

void SetHitIfNeeded(VirtualTrade &vt, int r_level, datetime utc_now)
{
   if(r_level == 1 && vt.hit1_utc == 0) vt.hit1_utc = utc_now;
   if(r_level == 2 && vt.hit2_utc == 0) vt.hit2_utc = utc_now;
   if(r_level == 3 && vt.hit3_utc == 0) vt.hit3_utc = utc_now;
   if(r_level == 4 && vt.hit4_utc == 0) vt.hit4_utc = utc_now;
   if(r_level == 5 && vt.hit5_utc == 0) vt.hit5_utc = utc_now;
}

bool AlreadyHit(VirtualTrade &vt, int r_level)
{
   if(r_level == 1) return vt.hit1_utc != 0;
   if(r_level == 2) return vt.hit2_utc != 0;
   if(r_level == 3) return vt.hit3_utc != 0;
   if(r_level == 4) return vt.hit4_utc != 0;
   if(r_level == 5) return vt.hit5_utc != 0;
   return true;
}

void ProcessTradeBar(VirtualTrade &vt, MqlRates &bar, datetime utc_now)
{
   datetime bar_close_server = bar.time + PeriodSeconds(PERIOD_M1);
   if(bar_close_server <= vt.entry_server_time)
      return;

   double fav = 0.0;
   double adv = 0.0;
   if(vt.side == SIDE_LONG)
   {
      fav = MathMax(0.0, bar.high - vt.entry) / vt.risk;
      adv = MathMax(0.0, vt.entry - bar.low) / vt.risk;
   }
   else
   {
      fav = MathMax(0.0, vt.entry - bar.low) / vt.risk;
      adv = MathMax(0.0, bar.high - vt.entry) / vt.risk;
   }
   vt.mfe_r = MathMax(vt.mfe_r, fav);
   vt.mae_r = MathMax(vt.mae_r, adv);

   bool stop_cross = false;
   if(vt.stop_utc == 0)
      stop_cross = (vt.side == SIDE_LONG ? bar.low <= vt.stop : bar.high >= vt.stop);

   bool new_positive_hit = false;
   for(int r=1; r<=5; r++)
   {
      if(AlreadyHit(vt,r)) continue;
      double target = (vt.side == SIDE_LONG ? vt.entry + r*vt.risk : vt.entry - r*vt.risk);
      bool crossed = (vt.side == SIDE_LONG ? bar.high >= target : bar.low <= target);
      if(crossed)
      {
         SetHitIfNeeded(vt,r,utc_now);
         new_positive_hit = true;
      }
   }

   if(stop_cross)
   {
      vt.stop_utc = utc_now;
      if(new_positive_hit)
      {
         vt.ambiguous = true;
         Print("[D025][AMBIGUOUS_M1] event=",vt.event_id," stop and new +R threshold first crossed in same M1 bar");
      }
   }

   long elapsed = (long)(utc_now - vt.entry_utc);
   if(!vt.h1_logged && elapsed >= 3600)
   {
      vt.h1_logged = true;
      LogOutcome(vt,"1H",utc_now);
   }
   if(!vt.h4_logged && elapsed >= 4*3600)
   {
      vt.h4_logged = true;
      LogOutcome(vt,"4H",utc_now);
   }
   if(!vt.h8_logged && elapsed >= 8*3600)
   {
      vt.h8_logged = true;
      LogOutcome(vt,"8H",utc_now);
   }
   if(!vt.h24_logged && elapsed >= 24*3600)
   {
      vt.h24_logged = true;
      LogOutcome(vt,"24H",utc_now);
   }
   if(!vt.h48_logged && elapsed >= 48*3600)
   {
      vt.h48_logged = true;
      LogOutcome(vt,"48H",utc_now);
      Print("[D025][48H_COMPLETE] event=",vt.event_id," MFE=",DoubleToString(vt.mfe_r,2),"R MAE=",DoubleToString(vt.mae_r,2),"R");
      vt.active = false;
   }
}

void ProcessM1Symbol(int symbol_index)
{
   string sym = g_symbols[symbol_index].symbol;
   datetime closed_open = iTime(sym, PERIOD_M1, 1);
   if(closed_open <= 0 || closed_open == g_symbols[symbol_index].last_m1_closed_open)
      return;

   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(sym, PERIOD_M1, 0, 2, rates) < 2)
      return;
   MqlRates bar = rates[1];
   g_symbols[symbol_index].last_m1_closed_open = closed_open;
   datetime utc_now = TimeGMT();

   for(int i=0;i<MAX_VIRTUAL_TRADES;i++)
   {
      if(g_trades[i].active && g_trades[i].symbol == sym)
         ProcessTradeBar(g_trades[i], bar, utc_now);
   }
}

int OnInit()
{
   g_session_id = StringFormat("D025V0_%I64d_%I64d", (long)TimeGMT(), (long)GetTickCount64());
   g_symbols[0].symbol = InpSymbol1;
   g_symbols[1].symbol = InpSymbol2;

   for(int s=0;s<SYMBOL_COUNT;s++)
   {
      g_symbols[s].atr_h1_handle = INVALID_HANDLE;
      g_symbols[s].last_m15_closed_open = 0;
      g_symbols[s].last_m1_closed_open = 0;
      g_symbols[s].ready = false;
      if(StringLen(g_symbols[s].symbol) == 0 || !SymbolSelect(g_symbols[s].symbol,true))
      {
         Print("[D025][FATAL] cannot select symbol: ",g_symbols[s].symbol);
         return INIT_FAILED;
      }
      g_symbols[s].atr_h1_handle = iATR(g_symbols[s].symbol, PERIOD_H1, 14);
      if(g_symbols[s].atr_h1_handle == INVALID_HANDLE)
      {
         Print("[D025][FATAL] cannot create H1 ATR handle for ",g_symbols[s].symbol," error=",GetLastError());
         return INIT_FAILED;
      }
      g_symbols[s].ready = true;
   }

   for(int s=0;s<SYMBOL_COUNT;s++)
   {
      for(int l=0;l<LEVEL_COUNT;l++)
      {
         int idx = TrackerIndex(s,l);
         g_trackers[idx].symbol_index = s;
         g_trackers[idx].level_index = l;
         g_trackers[idx].cooldown_until_utc = 0;
         ResetTracker(g_trackers[idx], false);
      }
   }
   for(int i=0;i<MAX_VIRTUAL_TRADES;i++)
      g_trades[i].active = false;

   EnsureCommonFolder();
   EventSetTimer(MathMax(1,InpTimerSeconds));
   Print("[D025][START] LER Observer V0 session=",g_session_id," symbols=",InpSymbol1,",",InpSymbol2," | CORE_MT5_ONLY | VIRTUAL_TRADES_ONLY | NO_ORDER_FUNCTIONS");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   int active_count = 0;
   for(int i=0;i<MAX_VIRTUAL_TRADES;i++)
      if(g_trades[i].active) active_count++;
   for(int s=0;s<SYMBOL_COUNT;s++)
      if(g_symbols[s].atr_h1_handle != INVALID_HANDLE) IndicatorRelease(g_symbols[s].atr_h1_handle);
   Print("[D025][STOP] session=",g_session_id," reason=",reason," active_virtual_trades_lost_on_restart=",active_count);
}

void OnTimer()
{
   for(int s=0;s<SYMBOL_COUNT;s++)
   {
      if(!g_symbols[s].ready) continue;
      ProcessM15Symbol(s);
      ProcessM1Symbol(s);
   }
}

void OnTick()
{
   // Deliberately empty. Research logic is timer-driven and multi-symbol.
}
