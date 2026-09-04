// D026 V0 implementation conformance fix.
// IMPORTANT: this is NOT a strategy retune. It preserves the pre-result V0 rules lock.
// It wraps V0 1.00 and replaces only the state-window enforcement and RETEST-band implementation.
// Keep this file in the same folder as D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5.

#define ProcessTracker ProcessTracker_V100_BUGGY
#define ProcessM15     ProcessM15_V100_BUGGY
#define OnTimer        OnTimer_V100_BUGGY
#include "D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5"
#undef ProcessTracker
#undef ProcessM15
#undef OnTimer

// Frozen-rule conformance corrections only:
// 1) SWEEP -> DISPLACEMENT: sweep bar or next 2 CLOSED M15 bars, not a third bar.
// 2) DISPLACEMENT -> EXHAUSTION: next 3 CLOSED M15 bars, not a fourth.
// 3) EXHAUSTION -> RECLAIM: next 4 CLOSED M15 bars, not a fifth.
// 4) RECLAIM -> VALID: next 4 CLOSED M15 bars, not a fifth.
// 5) RETEST proximity means the relevant extreme itself is within +/-0.15 H1 ATR of the level.

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
      // Frozen lock: only the next TWO closed M15 bars are eligible.
      if(tr.bars_in_state>2) { FailSequence(tr,"NO_DISPLACEMENT_2BARS",bar,utc_now); return; }
      double body_atr=0.0,body_eff=0.0,close_loc=0.0;
      if(IsDisplacement(side,bar,atr,range_shock,body_atr,body_eff,close_loc))
      {
         TransitionDisplacement(tr,bar,range_shock,body_atr,body_eff,close_loc,utc_now);
         return;
      }
      return;
   }

   if(tr.state==PER_DISPLACEMENT)
   {
      // Frozen lock: only the next THREE closed M15 bars are eligible.
      if(tr.bars_in_state>3) { FailSequence(tr,"NO_EXHAUSTION_3BARS",bar,utc_now); return; }
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
      return;
   }

   if(tr.state==PER_EXHAUSTION)
   {
      // Frozen lock: only the next FOUR closed M15 bars are eligible.
      if(tr.bars_in_state>4) { FailSequence(tr,"NO_RECLAIM_4BARS",bar,utc_now); return; }
      bool reclaimed=(side==SIDE_LONG ? bar.close>tr.frozen_level : bar.close<tr.frozen_level);
      if(reclaimed)
      {
         tr.state=PER_RECLAIM; tr.bars_in_state=0; tr.reclaim_utc=utc_now; tr.acceptance_closes=1;
         LogEvent(tr,"RECLAIM",utc_now,bar.time+PeriodSeconds(PERIOD_M15),range_shock,-1.0,-1.0,-1.0,-1.0,-1.0);
         return;
      }
      return;
   }

   if(tr.state==PER_RECLAIM)
   {
      // Frozen lock: only the next FOUR closed M15 bars are eligible.
      if(tr.bars_in_state>4) { FailSequence(tr,"NO_RETEST_ACCEPTANCE_4BARS",bar,utc_now); return; }
      bool inside_close=(side==SIDE_LONG ? bar.close>tr.frozen_level : bar.close<tr.frozen_level);
      double retest_band=RETEST_ATR*tr.atr_h1;
      bool retest=(side==SIDE_LONG ? (MathAbs(bar.low-tr.frozen_level)<=retest_band && bar.close>tr.frozen_level)
                                  : (MathAbs(bar.high-tr.frozen_level)<=retest_band && bar.close<tr.frozen_level));
      if(retest) { CreateVirtualTrade(tr,bar,"RETEST",utc_now); return; }
      if(inside_close) tr.acceptance_closes++; else tr.acceptance_closes=0;
      if(tr.acceptance_closes>=2) { CreateVirtualTrade(tr,bar,"ACCEPTANCE",utc_now); return; }
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

void OnTimer()
{
   ProcessM15();
   ProcessM1();
}
