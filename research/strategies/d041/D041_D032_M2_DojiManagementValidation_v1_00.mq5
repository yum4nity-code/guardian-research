#property strict
#property version   "1.00"
#property description "D041 operational wrapper for preregistered D032-M2 POST2024 Doji management validation - virtual only, no orders"

// ============================================================================
// D041_D032_M2_DojiManagementValidation
// SCIENTIFIC IDENTITY
//   Operational runner wrapper for the already-preregistered D032-M2 management
//   validation. This is NOT a new hypothesis and does NOT alter the D032 entry.
//   Canonical preregistration:
//   research/campaigns/D032_M2_DOJI_REALISTIC_MANAGEMENT_POST2024_VALIDATION_PREREGISTRATION_2026_09_05.md
//
// SOURCE LINEAGE
//   Exact D032-M1 source recovered from the user's ChatGPT file library with
//   historical SHA-256 6c55da90607d5431b92f9a59b2439ffa2e504b93621be78137dc99ab4fdef583.
//   Signal, trend, executable entry and source-R calculations are retained.
//
// FROZEN ENTRY
//   - Bullish Doji Star H1, TA-Lib-default numerical approximation used by D032.
//   - strict 144-hour SMA downtrend: MA[t-6] > ... > MA[t].
//   - LONG at first executable ASK after signal.
//   - source 1R = 2 * sample stdev(previous 24 H1 returns).
//
// FROZEN D032-M2 CANDIDATE
//   - hard catastrophe stop -3.5 source-R immediately after entry, actual BID fill.
//   - no TP/trail before +24h.
//   - at +24h: net ex-swap <=0 => full close; >0 => full runner.
//   - runner floor = net BE including frozen round-turn commission.
//   - runner trail = 1.5 source-R from highest post24 BID, no TP.
//   - hard timeout +48h from signal; gaps use first executable BID.
//
// REFERENCE
//   Same event, no hard stop, full exit at exact +24h BID.
//   Primary metric is paired candidate-minus-reference source-R/event.
//
// WINDOWS
//   Smoke uses already-seen PRE2024 data only. Formal validation uses POST2024
//   signal timestamps 2024-01-01 00:00 through 2026-06-23 23:00 server time.
//
// EXECUTION LIMITATION
//   Historical FundedNext real ticks are unavailable for much of this campaign.
//   Frozen runner model is MT5 Model=1 (1 minute OHLC). Positive stop-ordering
//   results remain provisional pending later real-tick/live-forward confirmation.
//
// NO ORDERS. GUARDIAN OFF.
// ============================================================================

input string InpRunTag = "";
input double InpCommissionBpsPerSide = 4.0; // frozen FundedNext crypto profile: 0.04% = 4 bps/side

#define M1_TREND_MA_HOURS 144
#define M1_SIGMA_RETURNS 24
#define M1_MAX_HOURS 48

string g_strategy="D041_D032_M2_DojiManagementValidation";
string g_classification="MANAGEMENT_VALIDATION_POST2024";
string SOURCE_NAME="D041_D032_M2_DojiManagementValidation_v1_00.mq5";
string SOURCE_VERSION="1.00";
string RUN_TOKEN="RUN";
string g_folder="";
string g_cohort="UNCLASSIFIED";

// PRE2024 is engineering smoke only; POST2024 is the preregistered management-validation window.
datetime g_pre_start       = D'2018.07.01 00:00';
datetime g_pre_last_signal = D'2023.12.29 23:00';
datetime g_post_start      = D'2024.01.01 00:00';
datetime g_post_last_signal= D'2026.06.23 23:00';

int g_evt_fh=INVALID_HANDLE;
int g_sum_fh=INVALID_HANDLE;
int g_info_fh=INVALID_HANDLE;

datetime g_first_tick=0;
datetime g_last_tick=0;
datetime g_last_h1_open=0;
int g_next_event_id=1;
int g_active_start=0;

int g_signals_seen=0;
int g_signals_accepted=0;
int g_events_complete=0;
int g_events_clean24=0;
int g_events_primary_eligible=0;
int g_primary_close24_nonpos=0;
int g_primary_stop=0;
int g_primary_timeout48=0;

double g_sum_baseline24_net_R=0.0;
double g_sum_primary48_net_R=0.0;
double g_sum_primary_delta_R=0.0;

long g_runner_rows=0;
long g_invalid_price=0;
long g_invalid_risk=0;
long g_pnl_calc_failures=0;
string g_fatal_status="";
string g_stats_name="";
string g_trades_name="";

struct RunnerState
  {
   bool activated;
   bool done;
   double trail_mult;
   int timeout_h;
   double peak_bid;
   double stop_price;
   datetime exit_time;
   double exit_price;
   string exit_reason;
  };

struct M1Event
  {
   int id;
   bool active;
   string epoch;
   datetime signal_end;
   datetime exec_entry_time;
   datetime finish_time;

   double source_entry;
   double exec_entry;
   double sigma24;
   double R_frac;
   double R_abs;
   double entry_spread_points;
   double commission_roundturn_bps;

   bool pre24_feed_gap;
   bool post24_feed_gap;
   int missing_horizons;
   int ticks_observed;

   // Raw path diagnostics in R from original executable entry.
   bool pre24_path_started;
   double pre24_mfe_R;
   double pre24_mae_R;
   bool post24_path_started;
   double post24_mfe_R;
   double post24_mae_R;

   bool hit_m15,hit_m20,hit_m25;
   datetime t_m15,t_m20,t_m25;

   // Exact-hour executable returns, bps from original entry.
   bool h24,h30,h36,h42,h48,h60,h72;
   double exe24,exe30,exe36,exe42,exe48,exe60,exe72;
   double bid24;
   datetime h24_time;

   bool h24_decision_done;
   bool h24_positive_net;
   double baseline24_net_R;
   double net_be_price;

   // Historical M1 runner fields retained only for source-lineage readability;
   // D041 formal output uses m2_candidate only.
   RunnerState r05_48;
   RunnerState r10_48;
   RunnerState r15_48;
   RunnerState r10_72;

   RunnerState m2_candidate;
   bool m2_catastrophe_hit;

   string terminal_reason;
  };

M1Event g_events[];

// ---------------------------------------------------------------------------
string SafeName(string s)
  {
   StringReplace(s,"\\","_"); StringReplace(s,"/","_"); StringReplace(s,":","_");
   StringReplace(s,"*","_"); StringReplace(s,"?","_"); StringReplace(s,"\"","_");
   StringReplace(s,"<","_"); StringReplace(s,">","_"); StringReplace(s,"|","_");
   return s;
  }
// ---------------------------------------------------------------------------
string Stamp(datetime t)
  {
   MqlDateTime d; TimeToStruct(t,d);
   return StringFormat("%04d%02d%02d_%02d%02d%02d",d.year,d.mon,d.day,d.hour,d.min,d.sec);
  }
// ---------------------------------------------------------------------------
string TS(datetime t)
  {
   if(t<=0) return "";
   return TimeToString(t,TIME_DATE|TIME_SECONDS);
  }
// ---------------------------------------------------------------------------
string F(double v)
  {
   if(v==EMPTY_VALUE) return "";
   return DoubleToString(v,6);
  }
// ---------------------------------------------------------------------------
string DetectCohort()
  {
   string s=_Symbol; StringToUpper(s);
   if(StringFind(s,"BTC")>=0) return "CORE_BTC";
   if(StringFind(s,"ETH")>=0) return "CORE_ETH";
   if(StringFind(s,"DOG")>=0) return "CORE_DOGE";
   return "UNREGISTERED";
  }
// ---------------------------------------------------------------------------
bool IsCoreCohort()
  {
   return (g_cohort=="CORE_BTC" || g_cohort=="CORE_ETH" || g_cohort=="CORE_DOGE");
  }
// ---------------------------------------------------------------------------
string EpochFor(datetime signal_end)
  {
   if(signal_end>=g_pre_start && signal_end<=g_pre_last_signal) return "PRE2024";
   if(signal_end>=g_post_start && signal_end<=g_post_last_signal) return "POST2024";
   return "OUTSIDE";
  }
// ---------------------------------------------------------------------------
bool GetH1(int shift,MqlRates &b)
  {
   MqlRates x[]; ArrayResize(x,1);
   if(CopyRates(_Symbol,PERIOD_H1,shift,1,x)!=1) return false;
   b=x[0];
   return (b.time>0 && b.close>0.0);
  }
// ---------------------------------------------------------------------------
double RealBody(MqlRates &b){return MathAbs(b.close-b.open);}
// ---------------------------------------------------------------------------
double AvgRealBody(int first_shift,int count)
  {
   double s=0.0;
   for(int k=0;k<count;k++)
     {
      MqlRates b; if(!GetH1(first_shift+k,b)) return -1.0;
      s+=MathAbs(b.close-b.open);
     }
   return (count>0 ? s/(double)count : -1.0);
  }
// ---------------------------------------------------------------------------
double AvgHighLow(int first_shift,int count)
  {
   double s=0.0;
   for(int k=0;k<count;k++)
     {
      MqlRates b; if(!GetH1(first_shift+k,b)) return -1.0;
      s+=(b.high-b.low);
     }
   return (count>0 ? s/(double)count : -1.0);
  }
// ---------------------------------------------------------------------------
double MA144AtOffset(int closed_offset)
  {
   double s=0.0;
   for(int j=0;j<M1_TREND_MA_HOURS;j++)
     {
      double c=iClose(_Symbol,PERIOD_H1,1+closed_offset+j);
      if(c<=0.0) return 0.0;
      s+=c;
     }
   return s/(double)M1_TREND_MA_HOURS;
  }
// ---------------------------------------------------------------------------
bool QualifyingDowntrend()
  {
   double ma[7];
   for(int chronological=0;chronological<7;chronological++)
     {
      int offset=6-chronological;
      ma[chronological]=MA144AtOffset(offset);
      if(ma[chronological]<=0.0) return false;
     }
   for(int i=1;i<7;i++) if(!(ma[i]<ma[i-1])) return false;
   return true;
  }
// ---------------------------------------------------------------------------
double Sigma24()
  {
   double r[M1_SIGMA_RETURNS]; double mean=0.0;
   for(int i=0;i<M1_SIGMA_RETURNS;i++)
     {
      double c0=iClose(_Symbol,PERIOD_H1,1+i);
      double c1=iClose(_Symbol,PERIOD_H1,2+i);
      if(c0<=0.0 || c1<=0.0) return 0.0;
      r[i]=c0/c1-1.0; mean+=r[i];
     }
   mean/=M1_SIGMA_RETURNS;
   double ss=0.0;
   for(int i=0;i<M1_SIGMA_RETURNS;i++){double d=r[i]-mean; ss+=d*d;}
   return MathSqrt(ss/(M1_SIGMA_RETURNS-1));
  }
// ---------------------------------------------------------------------------
bool BullishDojiStar()
  {
   MqlRates cur,prev;
   if(!GetH1(1,cur) || !GetH1(2,prev)) return false;
   double avgLong=AvgRealBody(3,10);
   double avgDojiHL=AvgHighLow(2,10);
   if(avgLong<=0.0 || avgDojiHL<=0.0) return false;
   bool prev_long_black=(prev.close<prev.open && RealBody(prev)>avgLong);
   bool cur_doji=(RealBody(cur)<=0.10*avgDojiHL);
   bool gap_down=(MathMax(cur.open,cur.close)<MathMin(prev.open,prev.close));
   return (prev_long_black && cur_doji && gap_down);
  }
// ---------------------------------------------------------------------------
double ExecEntryPrice(double &spread_points)
  {
   MqlTick t; spread_points=0.0;
   if(!SymbolInfoTick(_Symbol,t)) return 0.0;
   double pt=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(pt>0.0 && t.ask>0.0 && t.bid>0.0) spread_points=(t.ask-t.bid)/pt;
   return t.ask;
  }
// ---------------------------------------------------------------------------
double ExecExitPrice()
  {
   MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return 0.0;
   return t.bid;
  }
// ---------------------------------------------------------------------------
double DirectionalBps(double from,double to)
  {
   if(from<=0.0 || to<=0.0) return EMPTY_VALUE;
   return 10000.0*(to/from-1.0);
  }
// ---------------------------------------------------------------------------
double PriceToR(M1Event &e,double px)
  {
   if(e.R_abs<=0.0 || e.exec_entry<=0.0 || px<=0.0) return EMPTY_VALUE;
   return (px-e.exec_entry)/e.R_abs;
  }
// ---------------------------------------------------------------------------
double PriceNetR(M1Event &e,double px)
  {
   if(e.R_frac<=0.0) return EMPTY_VALUE;
   double bps=DirectionalBps(e.exec_entry,px);
   if(bps==EMPTY_VALUE) return EMPTY_VALUE;
   return ((bps-e.commission_roundturn_bps)/10000.0)/e.R_frac;
  }
// ---------------------------------------------------------------------------
double PriceGrossR(M1Event &e,double px)
  {
   if(e.R_frac<=0.0) return EMPTY_VALUE;
   double bps=DirectionalBps(e.exec_entry,px);
   if(bps==EMPTY_VALUE) return EMPTY_VALUE;
   return (bps/10000.0)/e.R_frac;
  }
// ---------------------------------------------------------------------------
double CommissionR(M1Event &e)
  {
   if(e.R_frac<=0.0) return EMPTY_VALUE;
   return (e.commission_roundturn_bps/10000.0)/e.R_frac;
  }
// ---------------------------------------------------------------------------
void InitRunner(RunnerState &r,double trail_mult,int timeout_h)
  {
   r.activated=false; r.done=false; r.trail_mult=trail_mult; r.timeout_h=timeout_h;
   r.peak_bid=0.0; r.stop_price=0.0; r.exit_time=0; r.exit_price=0.0; r.exit_reason="";
  }
// ---------------------------------------------------------------------------
void InitEvent(M1Event &e,datetime signal_end,double source_close,double sigma,datetime now,int id,string epoch)
  {
   e.id=id; e.active=true; e.epoch=epoch; e.signal_end=signal_end; e.exec_entry_time=now; e.finish_time=0;
   e.source_entry=source_close;
   double spread=0.0; e.exec_entry=ExecEntryPrice(spread); e.entry_spread_points=spread;
   e.sigma24=sigma; e.R_frac=2.0*sigma; e.R_abs=(e.exec_entry>0.0?e.exec_entry*e.R_frac:0.0);
   e.commission_roundturn_bps=2.0*InpCommissionBpsPerSide;
   e.pre24_feed_gap=false; e.post24_feed_gap=false; e.missing_horizons=0; e.ticks_observed=0;
   e.pre24_path_started=false; e.pre24_mfe_R=0.0; e.pre24_mae_R=0.0;
   e.post24_path_started=false; e.post24_mfe_R=0.0; e.post24_mae_R=0.0;
   e.hit_m15=false;e.hit_m20=false;e.hit_m25=false;e.t_m15=0;e.t_m20=0;e.t_m25=0;
   e.h24=false;e.h30=false;e.h36=false;e.h42=false;e.h48=false;e.h60=false;e.h72=false;
   e.exe24=EMPTY_VALUE;e.exe30=EMPTY_VALUE;e.exe36=EMPTY_VALUE;e.exe42=EMPTY_VALUE;
   e.exe48=EMPTY_VALUE;e.exe60=EMPTY_VALUE;e.exe72=EMPTY_VALUE;
   e.bid24=0.0;e.h24_time=0;e.h24_decision_done=false;e.h24_positive_net=false;
   e.baseline24_net_R=EMPTY_VALUE;e.net_be_price=0.0;
   InitRunner(e.r05_48,0.5,48); InitRunner(e.r10_48,1.0,48);
   InitRunner(e.r15_48,1.5,48); InitRunner(e.r10_72,1.0,72);
   InitRunner(e.m2_candidate,1.5,48); e.m2_catastrophe_hit=false;
   e.terminal_reason="";
  }
// ---------------------------------------------------------------------------
void RecordHardStopDiagnostics(M1Event &e,double r,datetime now)
  {
   if(r<=-1.5 && !e.hit_m15){e.hit_m15=true;e.t_m15=now;}
   if(r<=-2.0 && !e.hit_m20){e.hit_m20=true;e.t_m20=now;}
   if(r<=-2.5 && !e.hit_m25){e.hit_m25=true;e.t_m25=now;}
  }
// ---------------------------------------------------------------------------
void RunnerActivate(RunnerState &r,M1Event &e,double bid24)
  {
   r.activated=true; r.done=false; r.peak_bid=bid24;
   double trail_stop=bid24-r.trail_mult*e.R_abs;
   r.stop_price=MathMax(e.net_be_price,trail_stop);
  }
// ---------------------------------------------------------------------------
void RunnerClose(RunnerState &r,datetime now,double px,string reason)
  {
   if(r.done) return;
   r.done=true; r.exit_time=now; r.exit_price=px; r.exit_reason=reason;
  }
// ---------------------------------------------------------------------------
void MakeH24Decision(M1Event &e,datetime now,double bid24)
  {
   if(e.h24_decision_done || e.R_frac<=0.0 || bid24<=0.0) return;
   e.h24_decision_done=true; e.bid24=bid24; e.h24_time=now;
   e.baseline24_net_R=PriceNetR(e,bid24);

   double commission_frac=e.commission_roundturn_bps/10000.0;
   e.net_be_price=e.exec_entry*(1.0+commission_frac);
   e.h24_positive_net=(e.baseline24_net_R>0.0);

   // A pre24 catastrophe stop is final for the M2 candidate but does not alter
   // the no-stop +24h reference, which is still observed on the same event.
   if(e.m2_candidate.done) return;

   if(!e.h24_positive_net)
     {
      RunnerClose(e.m2_candidate,now,bid24,"CLOSE_H24_NONPOS");
      return;
     }

   RunnerActivate(e.m2_candidate,e,bid24);
  }
// ---------------------------------------------------------------------------
void UpdateOneRunner(RunnerState &r,M1Event &e,datetime now,double bid)
  {
   if(!r.activated || r.done || bid<=0.0) return;
   if(bid>r.peak_bid) r.peak_bid=bid;
   double new_stop=MathMax(e.net_be_price,r.peak_bid-r.trail_mult*e.R_abs);
   if(new_stop>r.stop_price) r.stop_price=new_stop;
   if(bid<=r.stop_price) RunnerClose(r,now,bid,"TRAIL_OR_BE_STOP");
  }
// ---------------------------------------------------------------------------
void UpdateActivePathsAndRunners(datetime now)
  {
   double bid=ExecExitPrice(); if(bid<=0.0){g_invalid_price++;return;}
   int n=ArraySize(g_events);
   for(int i=g_active_start;i<n;i++)
     {
      if(!g_events[i].active || g_events[i].R_abs<=0.0) continue;
      g_events[i].ticks_observed++;
      double r=PriceToR(g_events[i],bid); if(r==EMPTY_VALUE) continue;
      long secs=(long)(now-g_events[i].signal_end);

      if(secs<=24*3600)
        {
         if(!g_events[i].pre24_path_started){g_events[i].pre24_mfe_R=r;g_events[i].pre24_mae_R=r;g_events[i].pre24_path_started=true;}
         else {if(r>g_events[i].pre24_mfe_R)g_events[i].pre24_mfe_R=r; if(r<g_events[i].pre24_mae_R)g_events[i].pre24_mae_R=r;}

         // Frozen D032-M2 catastrophe stop: first executable BID at/below -3.5R.
         if(!g_events[i].m2_candidate.done && !g_events[i].h24_decision_done && r<=-3.5)
           {
            g_events[i].m2_catastrophe_hit=true;
            RunnerClose(g_events[i].m2_candidate,now,bid,"CATASTROPHE_STOP_PRE24");
           }
        }
      else
        {
         if(!g_events[i].post24_path_started){g_events[i].post24_mfe_R=r;g_events[i].post24_mae_R=r;g_events[i].post24_path_started=true;}
         else {if(r>g_events[i].post24_mfe_R)g_events[i].post24_mfe_R=r; if(r<g_events[i].post24_mae_R)g_events[i].post24_mae_R=r;}
         if(g_events[i].h24_decision_done && g_events[i].h24_positive_net && !g_events[i].m2_candidate.done)
            UpdateOneRunner(g_events[i].m2_candidate,g_events[i],now,bid);
        }
     }
  }
// ---------------------------------------------------------------------------
bool HorizonWanted(int h)
  {
   return (h==24 || h==48);
  }
// ---------------------------------------------------------------------------
void SetHorizon(M1Event &e,int h,double exe_bps,double bid,datetime now)
  {
   if(h==24){e.exe24=exe_bps;e.h24=true;MakeH24Decision(e,now,bid);}
   else if(h==30){e.exe30=exe_bps;e.h30=true;}
   else if(h==36){e.exe36=exe_bps;e.h36=true;}
   else if(h==42){e.exe42=exe_bps;e.h42=true;}
   else if(h==48){e.exe48=exe_bps;e.h48=true;}
   else if(h==60){e.exe60=exe_bps;e.h60=true;}
   else if(h==72){e.exe72=exe_bps;e.h72=true;}
  }
// ---------------------------------------------------------------------------
int MissingHorizonCount(M1Event &e)
  {
   int m=0;
   if(!e.h24)m++;
   return m;
  }
// ---------------------------------------------------------------------------
void EnforceRunnerTimeouts(M1Event &e,int h,datetime now,double bid)
  {
   if(h>=48 && e.m2_candidate.activated && !e.m2_candidate.done)
      RunnerClose(e.m2_candidate,now,bid,"TIMEOUT_48H");
  }
// ---------------------------------------------------------------------------
double RunnerNetR(M1Event &e,RunnerState &r)
  {
   if(!r.done || r.exit_price<=0.0) return EMPTY_VALUE;
   return PriceNetR(e,r.exit_price);
  }
// ---------------------------------------------------------------------------
bool EnsureOutput(datetime now)
  {
   if(g_evt_fh!=INVALID_HANDLE && g_sum_fh!=INVALID_HANDLE) return true;
   string sym=SafeName(_Symbol);
   g_trades_name="D041_V100_RUN_"+sym+"_TRADES.csv";
   g_stats_name="D041_V100_RUN_"+sym+"_STATS.csv";

   g_evt_fh=FileOpen(g_trades_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   g_sum_fh=FileOpen(g_stats_name,FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_evt_fh==INVALID_HANDLE || g_sum_fh==INVALID_HANDLE)
     {
      g_fatal_status="OUTPUT_OPEN_FAILED";
      Print("D041 OUTPUT ERROR: FileOpen failed | err=",GetLastError());
      return false;
     }

   FileWrite(g_evt_fh,
      "run_stage","symbol","cohort","epoch","trade_id","side",
      "signal_time","entry_time","exit_time","entry","exit",
      "sigma24","R_frac","R_abs","commission_roundturn_bps",
      "eligible","pre24_feed_gap","post24_feed_gap","candidate_catastrophe_hit",
      "reference_net_r","candidate_gross_r","commission_r","candidate_net_r","paired_delta_r","candidate_stress_net_r",
      "net_r","net_r_commission_x1_5","gross_r","exit_reason",
      "h24_positive_reference","h24_bid","net_be_price",
      "pre24_mfe_r","pre24_mae_r_signed","post24_mfe_r","post24_mae_r_signed",
      "candidate_peak_bid","candidate_stop_price","ticks_observed","terminal_reason");
   FileFlush(g_evt_fh);

   FileWrite(g_sum_fh,
      "status","source_name","source_version","run_stage","symbol",
      "trades_opened","trades_closed","csv_trade_rows",
      "invalid_price","invalid_risk","pnl_calc_failures","fatal_status",
      "signals_seen","events_clean24","candidate_eligible","commission_bps_per_side",
      "trades_name","stats_name");
   FileWrite(g_sum_fh,"INIT",SOURCE_NAME,SOURCE_VERSION,RUN_TOKEN,_Symbol,0,0,0,0,0,0,"",0,0,0,DoubleToString(InpCommissionBpsPerSide,4),g_trades_name,g_stats_name);
   FileWrite(g_sum_fh,"READY",SOURCE_NAME,SOURCE_VERSION,RUN_TOKEN,_Symbol,0,0,0,0,0,0,"",0,0,0,DoubleToString(InpCommissionBpsPerSide,4),g_trades_name,g_stats_name);
   FileFlush(g_sum_fh);

   if(FileSize(g_evt_fh)<300 || FileSize(g_sum_fh)<180)
     {
      g_fatal_status="OUTPUT_HEADER_QA_FAILED";
      Print("D041 FATAL OUTPUT QA: header file too small.");
      return false;
     }
   Print("D041 OUTPUT | FILE_COMMON\\",g_trades_name," | ",g_stats_name);
   return true;
  }
// ---------------------------------------------------------------------------
void WriteEvent(M1Event &e)
  {
   if(g_evt_fh==INVALID_HANDLE) return;

   double candidate=RunnerNetR(e,e.m2_candidate);
   double gross=(e.m2_candidate.done ? PriceGrossR(e,e.m2_candidate.exit_price) : EMPTY_VALUE);
   double comm=CommissionR(e);
   double delta=(candidate==EMPTY_VALUE || e.baseline24_net_R==EMPTY_VALUE ? EMPTY_VALUE : candidate-e.baseline24_net_R);
   double stress=(gross==EMPTY_VALUE || comm==EMPTY_VALUE ? EMPTY_VALUE : gross-1.5*comm);
   bool eligible=(e.epoch=="POST2024" && e.h24 && !e.pre24_feed_gap && e.baseline24_net_R!=EMPTY_VALUE && e.m2_candidate.done && candidate!=EMPTY_VALUE);

   FileWrite(g_evt_fh,
      RUN_TOKEN,_Symbol,g_cohort,e.epoch,StringFormat("%s_%d",SafeName(_Symbol),e.id),"LONG",
      TS(e.signal_end),TS(e.exec_entry_time),TS(e.m2_candidate.exit_time),
      DoubleToString(e.exec_entry,_Digits),DoubleToString(e.m2_candidate.exit_price,_Digits),
      DoubleToString(e.sigma24,8),DoubleToString(e.R_frac,8),DoubleToString(e.R_abs,_Digits),DoubleToString(e.commission_roundturn_bps,4),
      eligible?1:0,e.pre24_feed_gap?1:0,e.post24_feed_gap?1:0,e.m2_catastrophe_hit?1:0,
      F(e.baseline24_net_R),F(gross),F(comm),F(candidate),F(delta),F(stress),
      F(candidate),F(stress),F(gross),e.m2_candidate.exit_reason,
      e.h24_positive_net?1:0,DoubleToString(e.bid24,_Digits),DoubleToString(e.net_be_price,_Digits),
      F(e.pre24_mfe_R),F(e.pre24_mae_R),F(e.post24_mfe_R),F(e.post24_mae_R),
      DoubleToString(e.m2_candidate.peak_bid,_Digits),DoubleToString(e.m2_candidate.stop_price,_Digits),e.ticks_observed,e.terminal_reason);
   FileFlush(g_evt_fh);
   g_runner_rows++;
  }
// ---------------------------------------------------------------------------
void CompleteEvent(int i,string reason,datetime now)
  {
   if(!g_events[i].active) return;
   g_events[i].active=false;g_events[i].finish_time=now;g_events[i].terminal_reason=reason;
   g_events[i].missing_horizons=MissingHorizonCount(g_events[i]);
   g_events_complete++;

   bool clean24=(g_events[i].h24 && !g_events[i].pre24_feed_gap && g_events[i].exe24!=EMPTY_VALUE && g_events[i].R_frac>0.0 && g_events[i].h24_decision_done);
   if(clean24)
     {
      g_events_clean24++;
      if(g_events[i].m2_candidate.done)
        {
         double p=RunnerNetR(g_events[i],g_events[i].m2_candidate);
         if(p!=EMPTY_VALUE)
           {
            g_events_primary_eligible++;
            g_sum_baseline24_net_R+=g_events[i].baseline24_net_R;
            g_sum_primary48_net_R+=p;
            g_sum_primary_delta_R+=(p-g_events[i].baseline24_net_R);
            if(g_events[i].m2_candidate.exit_reason=="CLOSE_H24_NONPOS") g_primary_close24_nonpos++;
            else if(g_events[i].m2_candidate.exit_reason=="TRAIL_OR_BE_STOP" || g_events[i].m2_candidate.exit_reason=="CATASTROPHE_STOP_PRE24") g_primary_stop++;
            else if(g_events[i].m2_candidate.exit_reason=="TIMEOUT_48H") g_primary_timeout48++;
           }
        }
     }
   WriteEvent(g_events[i]);
  }
// ---------------------------------------------------------------------------
void AdvanceActiveStart()
  {
   int n=ArraySize(g_events);
   while(g_active_start<n && !g_events[g_active_start].active) g_active_start++;
  }
// ---------------------------------------------------------------------------
void FillHorizons(datetime current_h1_open)
  {
   int n=ArraySize(g_events); double bid=ExecExitPrice(); if(bid<=0.0) return;
   for(int i=g_active_start;i<n;i++)
     {
      if(!g_events[i].active) continue;
      long delta=(long)(current_h1_open-g_events[i].signal_end);
      if(delta<=0) continue;
      if((delta%3600)!=0)
        {
         if(delta<=24*3600)g_events[i].pre24_feed_gap=true;else g_events[i].post24_feed_gap=true;
         continue;
        }
      int h=(int)(delta/3600);
      if(HorizonWanted(h))
        {
         double exe=DirectionalBps(g_events[i].exec_entry,bid);
         SetHorizon(g_events[i],h,exe,bid,current_h1_open);
        }
      EnforceRunnerTimeouts(g_events[i],h,current_h1_open,bid);
      if(h>=M1_MAX_HOURS) CompleteEvent(i,"48H_COMPLETE",current_h1_open);
     }
  }
// ---------------------------------------------------------------------------
void ProcessClosedH1(datetime current_h1_open)
  {
   MqlRates closed; if(!GetH1(1,closed)) return;
   FillHorizons(current_h1_open); AdvanceActiveStart();

   if(Bars(_Symbol,PERIOD_H1)<M1_TREND_MA_HOURS+20) return;
   if(!QualifyingDowntrend()) return;
   double sigma=Sigma24(); if(sigma<=0.0 || !MathIsValidNumber(sigma)) return;
   g_signals_seen++;
   if(!BullishDojiStar()) return;

   datetime signal_end=current_h1_open;
   string epoch=EpochFor(signal_end);
   if(epoch=="OUTSIDE") return;

   int n=ArraySize(g_events); ArrayResize(g_events,n+1);
   InitEvent(g_events[n],signal_end,closed.close,sigma,current_h1_open,g_next_event_id++,epoch);
   if(g_events[n].exec_entry<=0.0 || g_events[n].R_abs<=0.0)
     {
      g_invalid_risk++; ArrayResize(g_events,n); return;
     }
   g_signals_accepted++;
   double entry_bid=ExecExitPrice();
   if(entry_bid>0.0)
     {
      double entry_r=PriceToR(g_events[n],entry_bid);
      if(entry_r!=EMPTY_VALUE && entry_r<=-3.5)
        {
         g_events[n].m2_catastrophe_hit=true;
         RunnerClose(g_events[n].m2_candidate,current_h1_open,entry_bid,"CATASTROPHE_STOP_PRE24");
        }
     }
   Print("D041 SIGNAL | ",_Symbol," | ",g_cohort," | ",epoch," | ",TS(signal_end));
  }
// ---------------------------------------------------------------------------
void WriteSummary()
  {
   if(g_sum_fh==INVALID_HANDLE) return;
   FileWrite(g_sum_fh,"FINAL",SOURCE_NAME,SOURCE_VERSION,RUN_TOKEN,_Symbol,
      g_signals_accepted,g_runner_rows,g_runner_rows,
      g_invalid_price,g_invalid_risk,g_pnl_calc_failures,g_fatal_status,
      g_signals_seen,g_events_clean24,g_events_primary_eligible,DoubleToString(InpCommissionBpsPerSide,4),
      g_trades_name,g_stats_name);
   FileFlush(g_sum_fh);
  }
// ---------------------------------------------------------------------------
int OnInit()
  {
   ArrayResize(g_events,0); g_cohort=DetectCohort();
   if(_Period!=PERIOD_M1)
     {
      Print("D041 FATAL: tester chart timeframe must be M1");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(!IsCoreCohort())
     {
      Print("D041 FATAL: only BTC/ETH/DOG core cohort is allowed");
      return INIT_PARAMETERS_INCORRECT;
     }
   Print("D041 INIT | ",_Symbol," | cohort=",g_cohort,
         " | EXACT D032-M2: -3.5R catastrophe; H24 nonpos close; H24 positive => net-BE + 1.5R trail to H48 | NO TP | NO ORDERS");
   return INIT_SUCCEEDED;
  }
// ---------------------------------------------------------------------------
void OnTick()
  {
   datetime now=TimeCurrent(); if(now<=0) return;
   if(g_first_tick==0)
     {
      g_first_tick=now;
      if(!EnsureOutput(now))
        {
         Print("D041 FATAL: output initialization/QA failed.");
         ExpertRemove(); return;
        }
     }
   g_last_tick=now;
   UpdateActivePathsAndRunners(now);

   datetime h1open=iTime(_Symbol,PERIOD_H1,0); if(h1open<=0) return;
   if(g_last_h1_open==0){g_last_h1_open=h1open;return;}
   if(h1open!=g_last_h1_open)
     {
      long gap=(long)(h1open-g_last_h1_open);
      if(gap!=3600)
        {
         for(int i=g_active_start;i<ArraySize(g_events);i++)
           {
            if(!g_events[i].active) continue;
            long age=(long)(h1open-g_events[i].signal_end);
            if(age<=24*3600) g_events[i].pre24_feed_gap=true;
            else g_events[i].post24_feed_gap=true;
           }
        }
      g_last_h1_open=h1open;
      ProcessClosedH1(h1open);
     }
  }
// ---------------------------------------------------------------------------
void OnDeinit(const int reason)
  {
   datetime now=(g_last_tick>0?g_last_tick:TimeCurrent());
   for(int i=g_active_start;i<ArraySize(g_events);i++)
      if(g_events[i].active) CompleteEvent(i,"EOT_INCOMPLETE",now);
   WriteSummary();

   if(g_evt_fh!=INVALID_HANDLE){FileFlush(g_evt_fh);FileClose(g_evt_fh);g_evt_fh=INVALID_HANDLE;}
   if(g_sum_fh!=INVALID_HANDLE){FileFlush(g_sum_fh);FileClose(g_sum_fh);g_sum_fh=INVALID_HANDLE;}
   if(g_info_fh!=INVALID_HANDLE){FileFlush(g_info_fh);FileClose(g_info_fh);g_info_fh=INVALID_HANDLE;}

   Print("D041 SUMMARY | symbol=",_Symbol," | cohort=",g_cohort,
         " | accepted=",g_signals_accepted," | clean24=",g_events_clean24,
         " | eligible=",g_events_primary_eligible," | rows=",g_runner_rows);
  }
// ============================================================================
