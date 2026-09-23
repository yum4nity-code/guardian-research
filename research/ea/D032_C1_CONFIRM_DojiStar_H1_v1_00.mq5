#property strict
#property version   "1.00"
#property description "D032-C1 Doji Star H1 confirmation scanner - virtual only, no orders"

// ============================================================================
// D032_C1_CONFIRM_DojiStar_H1
// PURPOSE: confirm the D032 Bullish Doji Star H1 discovery on untouched CFD data.
// NO ORDERS. NO GUARDIAN. NO PARAMETER SEARCH.
//
// Discovery sample already seen: 2024-01-01 through 2026-06-26.
// This confirmation scanner ONLY accepts signals in the untouched historical
// window 2018-07-01 through 2023-12-30 23:00 server time.  The last accepted
// signal therefore has its full 24h outcome before 2024-01-01.
//
// Frozen core confirmation cohort:
//   BTC CFD, ETH CFD, DOGE/DOG CFD
// Frozen transport-only cohort:
//   LINK/LNK CFD, XRP CFD
//
// Signal logic is unchanged from D032:
//   - Bullish Doji Star, TA-Lib default numerical candle settings.
//   - Qualifying prior downtrend:
//       144-hour SMA, strict MA[t-6] > ... > MA[t].
//   - Signal complete at end of H1 pattern candle.
//   - Executable LONG entry = first available ASK after signal.
//   - Source entry = H1 pattern close.
//   - Primary endpoint = executable bid return at +24h.
//   - 1R = 2 * sample stdev(previous 24 H1 returns).
//
// Secondary management hypothesis, frozen BEFORE confirmation results:
//   LONG -> stop -1R -> target +3R -> otherwise timeout at +24h.
// First-touch ordering uses real tester ticks.
//
// Source horizons are retained as diagnostics only:
//   1,2,3,6,9,12,15,18,24 hours.
//
// Output contract:
// FILE_COMMON\GuardianResearch\SETUP_SCANS\D032_C1_CONFIRM_DojiStar_H1\
//   <SYMBOL>\RUN_...\
//     CONFIRM_EVENTS.csv
//     CONTROL_POOL.csv
//     SUMMARY.csv
//     RUN_INFO.csv
//
// IMPORTANT:
// - Run M1 + "Every tick based on real ticks".
// - Use tester dates covering pre-2024 history; recommended 2018-07-01..2024-01-01.
// - If the broker has less history, the scanner uses only what exists.
// - 2024+ signals are deliberately ignored and cannot contaminate confirmation.
// ============================================================================

input bool   InpWriteControlPool = true;
input string InpRunTag = "";
input double InpCommissionBpsPerSide = 0.0; // spread is already embedded in executable bid/ask

#define C1_TREND_MA_HOURS 144
#define C1_SIGMA_RETURNS 24
#define C1_MAX_HOURS 24

string g_strategy = "D032_C1_CONFIRM_DojiStar_H1";
string g_classification = "CONFIRMATION_CLOSE_REPLICATION_CFD_TRANSFER";
datetime g_confirm_start = D'2018.07.01 00:00';
datetime g_confirm_last_signal = D'2023.12.30 23:00';

string g_folder="";
string g_cohort="UNCLASSIFIED";

int g_evt_fh=INVALID_HANDLE;
int g_ctl_fh=INVALID_HANDLE;
int g_sum_fh=INVALID_HANDLE;
int g_info_fh=INVALID_HANDLE;

datetime g_first_tick=0;
datetime g_last_tick=0;
datetime g_last_h1_open=0;

int g_next_event_id=1;
int g_next_control_id=1;
int g_event_active_start=0;
int g_control_active_start=0;

int g_signals_seen=0;
int g_signals_accepted=0;
int g_signals_before_window=0;
int g_signals_after_window=0;
int g_events_complete=0;
int g_events_clean24=0;
int g_events_feedgap=0;
int g_controls_complete=0;
int g_controls_clean24=0;

double g_sum_exec24_bps=0.0;
double g_sum_net24_bps=0.0;
double g_sum_exec24_R=0.0;
double g_sum_mgmt_R=0.0;
int g_mgmt_stop=0;
int g_mgmt_target=0;
int g_mgmt_timeout=0;
int g_exec24_positive=0;

struct C1Event
  {
   int id;
   bool active;
   bool is_control;
   string label;
   int dir;

   datetime signal_end;
   datetime exec_entry_time;
   datetime finish_time;

   double source_entry;
   double exec_entry;
   double sigma24;
   double R_frac;
   double exec_R_abs;
   double entry_spread_points;
   double commission_roundturn_bps;

   bool feed_gap;
   int missing_horizons;
   int ticks_observed;

   // Path on real ticks for pattern events only.
   bool path_started;
   double mfe_R;
   double mae_R;
   bool hit05,hit10,hit15,hit20,hit25,hit30;
   datetime t05,t10,t15,t20,t25,t30;
   bool neg1_hit;
   datetime neg1_time;

   // Frozen secondary management: first of -1R / +3R, else 24h timeout.
   bool mgmt_done;
   string mgmt_reason;
   datetime mgmt_exit_time;
   double mgmt_exit_R_actual;

   // Source and executable directional returns, bps.
   double src1,src2,src3,src6,src9,src12,src15,src18,src24;
   double exe1,exe2,exe3,exe6,exe9,exe12,exe15,exe18,exe24;
   bool h1,h2,h3,h6,h9,h12,h15,h18,h24;

   string terminal_reason;
  };

C1Event g_events[];
C1Event g_controls[];

// ---------------------------------------------------------------------------
string SafeName(string s)
  {
   StringReplace(s,"\\","_");
   StringReplace(s,"/","_");
   StringReplace(s,":","_");
   StringReplace(s,"*","_");
   StringReplace(s,"?","_");
   StringReplace(s,"\"","_");
   StringReplace(s,"<","_");
   StringReplace(s,">","_");
   StringReplace(s,"|","_");
   return s;
  }
// ---------------------------------------------------------------------------
string Stamp(datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t,d);
   return StringFormat("%04d%02d%02d_%02d%02d%02d",
                       d.year,d.mon,d.day,d.hour,d.min,d.sec);
  }
// ---------------------------------------------------------------------------
string TS(datetime t)
  {
   if(t<=0) return "";
   return TimeToString(t,TIME_DATE|TIME_SECONDS);
  }
// ---------------------------------------------------------------------------
string DetectCohort()
  {
   string s=_Symbol;
   StringToUpper(s);
   if(StringFind(s,"BTC")>=0) return "CORE_BTC";
   if(StringFind(s,"ETH")>=0) return "CORE_ETH";
   if(StringFind(s,"DOG")>=0) return "CORE_DOGE";
   if(StringFind(s,"LINK")>=0 || StringFind(s,"LNK")>=0) return "TRANSPORT_LINK";
   if(StringFind(s,"XRP")>=0) return "TRANSPORT_XRP";
   return "UNREGISTERED_TRANSPORT";
  }
// ---------------------------------------------------------------------------
bool GetH1(int shift,MqlRates &b)
  {
   MqlRates x[];
   ArrayResize(x,1);
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
      MqlRates b;
      if(!GetH1(first_shift+k,b)) return -1.0;
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
      MqlRates b;
      if(!GetH1(first_shift+k,b)) return -1.0;
      s+=(b.high-b.low);
     }
   return (count>0 ? s/(double)count : -1.0);
  }
// ---------------------------------------------------------------------------
double MA144AtOffset(int closed_offset)
  {
   double s=0.0;
   for(int j=0;j<C1_TREND_MA_HOURS;j++)
     {
      double c=iClose(_Symbol,PERIOD_H1,1+closed_offset+j);
      if(c<=0.0) return 0.0;
      s+=c;
     }
   return s/(double)C1_TREND_MA_HOURS;
  }
// ---------------------------------------------------------------------------
bool QualifyingDowntrend()
  {
   double ma[7];
   // chronological old -> new: MA[t-6] ... MA[t]
   for(int chronological=0;chronological<7;chronological++)
     {
      int offset=6-chronological;
      ma[chronological]=MA144AtOffset(offset);
      if(ma[chronological]<=0.0) return false;
     }
   for(int i=1;i<7;i++)
      if(!(ma[i]<ma[i-1])) return false;
   return true;
  }
// ---------------------------------------------------------------------------
double Sigma24()
  {
   double r[C1_SIGMA_RETURNS];
   double mean=0.0;
   for(int i=0;i<C1_SIGMA_RETURNS;i++)
     {
      double c0=iClose(_Symbol,PERIOD_H1,1+i);
      double c1=iClose(_Symbol,PERIOD_H1,2+i);
      if(c0<=0.0 || c1<=0.0) return 0.0;
      r[i]=c0/c1-1.0;
      mean+=r[i];
     }
   mean/=C1_SIGMA_RETURNS;

   double ss=0.0;
   for(int i=0;i<C1_SIGMA_RETURNS;i++)
     {
      double d=r[i]-mean;
      ss+=d*d;
     }
   return MathSqrt(ss/(C1_SIGMA_RETURNS-1));
  }
// ---------------------------------------------------------------------------
bool BullishDojiStar()
  {
   MqlRates cur,prev;
   if(!GetH1(1,cur) || !GetH1(2,prev)) return false;

   // TA-Lib CDLDOJISTAR bullish output under default candle settings:
   // previous candle: long black real body (> avg previous 10 real bodies)
   // current candle: doji (<= 10% avg previous 10 high-low ranges)
   // current real body gaps down below previous real body.
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
   MqlTick t;
   spread_points=0.0;
   if(!SymbolInfoTick(_Symbol,t)) return 0.0;
   double pt=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(pt>0.0 && t.ask>0.0 && t.bid>0.0)
      spread_points=(t.ask-t.bid)/pt;
   return t.ask; // LONG
  }
// ---------------------------------------------------------------------------
double ExecExitPrice()
  {
   MqlTick t;
   if(!SymbolInfoTick(_Symbol,t)) return 0.0;
   return t.bid; // LONG exit
  }
// ---------------------------------------------------------------------------
double DirectionalBps(double from,double to)
  {
   if(from<=0.0 || to<=0.0) return EMPTY_VALUE;
   return 10000.0*(to/from-1.0); // LONG only
  }
// ---------------------------------------------------------------------------
string F(double v)
  {
   if(v==EMPTY_VALUE) return "";
   return DoubleToString(v,6);
  }
// ---------------------------------------------------------------------------
bool HorizonWanted(int h)
  {
   return (h==1 || h==2 || h==3 || h==6 || h==9 ||
           h==12 || h==15 || h==18 || h==24);
  }
// ---------------------------------------------------------------------------
void SetHorizon(C1Event &e,int h,double src_bps,double exe_bps)
  {
   if(h==1){e.src1=src_bps;e.exe1=exe_bps;e.h1=true;}
   else if(h==2){e.src2=src_bps;e.exe2=exe_bps;e.h2=true;}
   else if(h==3){e.src3=src_bps;e.exe3=exe_bps;e.h3=true;}
   else if(h==6){e.src6=src_bps;e.exe6=exe_bps;e.h6=true;}
   else if(h==9){e.src9=src_bps;e.exe9=exe_bps;e.h9=true;}
   else if(h==12){e.src12=src_bps;e.exe12=exe_bps;e.h12=true;}
   else if(h==15){e.src15=src_bps;e.exe15=exe_bps;e.h15=true;}
   else if(h==18){e.src18=src_bps;e.exe18=exe_bps;e.h18=true;}
   else if(h==24){e.src24=src_bps;e.exe24=exe_bps;e.h24=true;}
  }
// ---------------------------------------------------------------------------
int MissingHorizonCount(C1Event &e)
  {
   int m=0;
   if(!e.h1)m++; if(!e.h2)m++; if(!e.h3)m++;
   if(!e.h6)m++; if(!e.h9)m++; if(!e.h12)m++;
   if(!e.h15)m++; if(!e.h18)m++; if(!e.h24)m++;
   return m;
  }
// ---------------------------------------------------------------------------
void InitEvent(C1Event &e,bool control,string label,datetime signal_end,
               double source_close,double sigma,datetime now,int id)
  {
   e.id=id;
   e.active=true;
   e.is_control=control;
   e.label=label;
   e.dir=+1;
   e.signal_end=signal_end;
   e.exec_entry_time=now;
   e.finish_time=0;
   e.source_entry=source_close;

   double spread=0.0;
   e.exec_entry=ExecEntryPrice(spread);
   e.entry_spread_points=spread;
   e.sigma24=sigma;
   e.R_frac=2.0*sigma;
   e.exec_R_abs=(e.exec_entry>0.0 ? e.exec_entry*e.R_frac : 0.0);
   e.commission_roundturn_bps=2.0*InpCommissionBpsPerSide;

   e.feed_gap=false;
   e.missing_horizons=0;
   e.ticks_observed=0;

   e.path_started=false;
   e.mfe_R=0.0;e.mae_R=0.0;
   e.hit05=false;e.hit10=false;e.hit15=false;e.hit20=false;e.hit25=false;e.hit30=false;
   e.t05=0;e.t10=0;e.t15=0;e.t20=0;e.t25=0;e.t30=0;
   e.neg1_hit=false;e.neg1_time=0;

   e.mgmt_done=false;
   e.mgmt_reason="";
   e.mgmt_exit_time=0;
   e.mgmt_exit_R_actual=0.0;

   e.src1=EMPTY_VALUE;e.src2=EMPTY_VALUE;e.src3=EMPTY_VALUE;e.src6=EMPTY_VALUE;
   e.src9=EMPTY_VALUE;e.src12=EMPTY_VALUE;e.src15=EMPTY_VALUE;e.src18=EMPTY_VALUE;e.src24=EMPTY_VALUE;
   e.exe1=EMPTY_VALUE;e.exe2=EMPTY_VALUE;e.exe3=EMPTY_VALUE;e.exe6=EMPTY_VALUE;
   e.exe9=EMPTY_VALUE;e.exe12=EMPTY_VALUE;e.exe15=EMPTY_VALUE;e.exe18=EMPTY_VALUE;e.exe24=EMPTY_VALUE;

   e.h1=false;e.h2=false;e.h3=false;e.h6=false;e.h9=false;
   e.h12=false;e.h15=false;e.h18=false;e.h24=false;
   e.terminal_reason="";
  }
// ---------------------------------------------------------------------------
void MarkPositiveLevels(C1Event &e,double r,datetime now)
  {
   if(r>=0.5 && !e.hit05){e.hit05=true;e.t05=now;}
   if(r>=1.0 && !e.hit10){e.hit10=true;e.t10=now;}
   if(r>=1.5 && !e.hit15){e.hit15=true;e.t15=now;}
   if(r>=2.0 && !e.hit20){e.hit20=true;e.t20=now;}
   if(r>=2.5 && !e.hit25){e.hit25=true;e.t25=now;}
   if(r>=3.0 && !e.hit30){e.hit30=true;e.t30=now;}
  }
// ---------------------------------------------------------------------------
void UpdatePatternPaths(datetime now)
  {
   int n=ArraySize(g_events);
   for(int i=g_event_active_start;i<n;i++)
     {
      if(!g_events[i].active) continue;
      if(g_events[i].exec_R_abs<=0.0 || g_events[i].exec_entry<=0.0) continue;

      double px=ExecExitPrice();
      if(px<=0.0) continue;

      double r=(px-g_events[i].exec_entry)/g_events[i].exec_R_abs;
      g_events[i].ticks_observed++;

      if(!g_events[i].path_started)
        {
         g_events[i].mfe_R=r;
         g_events[i].mae_R=r;
         g_events[i].path_started=true;
        }
      else
        {
         if(r>g_events[i].mfe_R) g_events[i].mfe_R=r;
         if(r<g_events[i].mae_R) g_events[i].mae_R=r;
        }

      MarkPositiveLevels(g_events[i],r,now);

      if(r<=-1.0 && !g_events[i].neg1_hit)
        {
         g_events[i].neg1_hit=true;
         g_events[i].neg1_time=now;
        }

      // Frozen secondary management first-touch policy.
      if(!g_events[i].mgmt_done)
        {
         if(r<=-1.0)
           {
            g_events[i].mgmt_done=true;
            g_events[i].mgmt_reason="STOP_-1R_FIRST";
            g_events[i].mgmt_exit_time=now;
            g_events[i].mgmt_exit_R_actual=r;
           }
         else if(r>=3.0)
           {
            g_events[i].mgmt_done=true;
            g_events[i].mgmt_reason="TARGET_3R_FIRST";
            g_events[i].mgmt_exit_time=now;
            g_events[i].mgmt_exit_R_actual=r;
           }
        }
     }
  }
// ---------------------------------------------------------------------------
bool EnsureOutput(datetime now)
  {
   if(g_evt_fh!=INVALID_HANDLE) return true;

   string tag=InpRunTag;
   if(StringLen(tag)==0)
     {
      ulong gt=GetTickCount64();
      tag="RUN_"+Stamp(now)+"_"+IntegerToString((int)(gt%1000000));
     }
   tag=SafeName(tag);

   g_folder="GuardianResearch\\SETUP_SCANS\\"+g_strategy+"\\"+
            SafeName(_Symbol)+"\\"+tag;

   if(!FolderCreate(g_folder,FILE_COMMON))
     {
      Print("D032-C1 OUTPUT ERROR: FolderCreate failed | ",g_folder,
            " | err=",GetLastError());
      return false;
     }

   g_evt_fh=FileOpen(g_folder+"\\CONFIRM_EVENTS.csv",
                     FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   if(InpWriteControlPool)
      g_ctl_fh=FileOpen(g_folder+"\\CONTROL_POOL.csv",
                        FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   g_sum_fh=FileOpen(g_folder+"\\SUMMARY.csv",
                     FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');
   g_info_fh=FileOpen(g_folder+"\\RUN_INFO.csv",
                      FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,';');

   if(g_evt_fh==INVALID_HANDLE || g_sum_fh==INVALID_HANDLE || g_info_fh==INVALID_HANDLE ||
      (InpWriteControlPool && g_ctl_fh==INVALID_HANDLE))
     {
      Print("D032-C1 OUTPUT ERROR: FileOpen failed | err=",GetLastError());
      return false;
     }

   // Explicit headers: no index array, so header bounds cannot fail silently.
   FileWrite(g_evt_fh,
      "strategy_id","classification","cohort","symbol","row_type","event_id",
      "signal_end_server","exec_entry_time_server","finish_time_server",
      "source_entry_close","exec_entry_ask","sigma24","R_frac_2sigma","exec_R_abs",
      "entry_spread_points","commission_roundturn_bps","feed_gap","missing_horizons",
      "MFE_R_24h","MAE_R_24h",
      "hit_0_5R","time_0_5R","hit_1R","time_1R","hit_1_5R","time_1_5R",
      "hit_2R","time_2R","hit_2_5R","time_2_5R","hit_3R","time_3R",
      "neg_1R_hit","neg_1R_time",
      "mgmt_reason","mgmt_exit_time","mgmt_exit_R_actual","mgmt_net_R",
      "src_bps_1h","src_bps_2h","src_bps_3h","src_bps_6h","src_bps_9h",
      "src_bps_12h","src_bps_15h","src_bps_18h","src_bps_24h",
      "exe_bps_1h","exe_bps_2h","exe_bps_3h","exe_bps_6h","exe_bps_9h",
      "exe_bps_12h","exe_bps_15h","exe_bps_18h","exe_bps_24h",
      "net_exe_bps_24h","exe_24h_R","terminal_reason","ticks_observed");
   FileFlush(g_evt_fh);

   if(g_ctl_fh!=INVALID_HANDLE)
     {
      FileWrite(g_ctl_fh,
         "strategy_id","classification","cohort","symbol","row_type","control_id",
         "signal_end_server","exec_entry_time_server","finish_time_server",
         "source_entry_close","exec_entry_ask","sigma24","R_frac_2sigma",
         "entry_spread_points","commission_roundturn_bps","feed_gap","missing_horizons",
         "src_bps_1h","src_bps_2h","src_bps_3h","src_bps_6h","src_bps_9h",
         "src_bps_12h","src_bps_15h","src_bps_18h","src_bps_24h",
         "exe_bps_1h","exe_bps_2h","exe_bps_3h","exe_bps_6h","exe_bps_9h",
         "exe_bps_12h","exe_bps_15h","exe_bps_18h","exe_bps_24h",
         "net_exe_bps_24h","exe_24h_R","terminal_reason");
      FileFlush(g_ctl_fh);
     }

   FileWrite(g_sum_fh,
      "strategy_id","cohort","symbol","signals_seen","signals_accepted",
      "events_complete","events_clean24","events_feedgap",
      "mean_exec24_bps_clean","mean_net24_bps_clean","mean_exec24_R_clean",
      "winrate_exec24_clean_pct","mean_secondary_mgmt_net_R_clean",
      "mgmt_stop_count","mgmt_target_count","mgmt_timeout_count",
      "controls_complete","controls_clean24");
   FileFlush(g_sum_fh);

   FileWrite(g_info_fh,"key","value");
   FileWrite(g_info_fh,"strategy_id",g_strategy);
   FileWrite(g_info_fh,"classification",g_classification);
   FileWrite(g_info_fh,"symbol",_Symbol);
   FileWrite(g_info_fh,"cohort",g_cohort);
   FileWrite(g_info_fh,"orders_sent","0");
   FileWrite(g_info_fh,"guardian_used","0");
   FileWrite(g_info_fh,"signal_tf","H1");
   FileWrite(g_info_fh,"recommended_tester_chart_tf","M1");
   FileWrite(g_info_fh,"recommended_tester_model","Every tick based on real ticks");
   FileWrite(g_info_fh,"discovery_sample_seen","2024-01-01 through 2026-06-26");
   FileWrite(g_info_fh,"confirmation_signal_start",TS(g_confirm_start));
   FileWrite(g_info_fh,"confirmation_last_signal",TS(g_confirm_last_signal));
   FileWrite(g_info_fh,"confirmation_rule","Signals outside frozen pre-2024 window are ignored");
   FileWrite(g_info_fh,"pattern","Bullish Doji Star only");
   FileWrite(g_info_fh,"pattern_engine","TA-Lib default CDLDOJISTAR bullish definition reimplemented numerically");
   FileWrite(g_info_fh,"trend_rule","144-hour SMA; strict MA[t-6] > ... > MA[t] downtrend");
   FileWrite(g_info_fh,"primary_endpoint","clean executable LONG return at +24h");
   FileWrite(g_info_fh,"primary_risk_normalization","1R = 2 * sample stdev previous 24 H1 returns");
   FileWrite(g_info_fh,"secondary_management","LONG; first touch -1R stop or +3R target; else +24h timeout");
   FileWrite(g_info_fh,"secondary_management_status","post-discovery hypothesis frozen before confirmation outcomes");
   FileWrite(g_info_fh,"diagnostic_horizons_hours","1,2,3,6,9,12,15,18,24");
   FileWrite(g_info_fh,"commission_bps_per_side",DoubleToString(InpCommissionBpsPerSide,4));
   FileWrite(g_info_fh,"spread_handling","Executable entry ASK and future exits BID");
   FileWrite(g_info_fh,"control_pool","same qualifying downtrend, no bullish Doji Star");
   FileWrite(g_info_fh,"output_folder",g_folder);
   FileWrite(g_info_fh,"first_tick_server",TS(now));
   FileFlush(g_info_fh);

   // Runtime output QA: every file must contain a real header, not a BOM-only shell.
   if(FileSize(g_evt_fh)<200 || FileSize(g_sum_fh)<100 || FileSize(g_info_fh)<200 ||
      (g_ctl_fh!=INVALID_HANDLE && FileSize(g_ctl_fh)<150))
     {
      Print("D032-C1 FATAL OUTPUT QA: header file too small. Do not use this run.");
      return false;
     }

   Print("D032-C1 OUTPUT | FILE_COMMON\\",g_folder);
   return true;
  }
// ---------------------------------------------------------------------------
void WriteEvent(C1Event &e)
  {
   if(g_evt_fh==INVALID_HANDLE) return;

   double net24=(e.exe24==EMPTY_VALUE ? EMPTY_VALUE :
                 e.exe24-e.commission_roundturn_bps);
   double r24=(e.exe24==EMPTY_VALUE || e.R_frac<=0.0 ? EMPTY_VALUE :
               (e.exe24/10000.0)/e.R_frac);
   double mgmt_net_R=(e.R_frac>0.0 ?
                      e.mgmt_exit_R_actual-(e.commission_roundturn_bps/10000.0)/e.R_frac :
                      EMPTY_VALUE);

   FileWrite(g_evt_fh,
      g_strategy,g_classification,g_cohort,_Symbol,"CONFIRM_PATTERN",e.id,
      TS(e.signal_end),TS(e.exec_entry_time),TS(e.finish_time),
      DoubleToString(e.source_entry,_Digits),DoubleToString(e.exec_entry,_Digits),
      DoubleToString(e.sigma24,8),DoubleToString(e.R_frac,8),
      DoubleToString(e.exec_R_abs,_Digits),DoubleToString(e.entry_spread_points,2),
      DoubleToString(e.commission_roundturn_bps,4),
      (e.feed_gap?1:0),e.missing_horizons,
      DoubleToString(e.mfe_R,6),DoubleToString(e.mae_R,6),
      (e.hit05?1:0),TS(e.t05),(e.hit10?1:0),TS(e.t10),
      (e.hit15?1:0),TS(e.t15),(e.hit20?1:0),TS(e.t20),
      (e.hit25?1:0),TS(e.t25),(e.hit30?1:0),TS(e.t30),
      (e.neg1_hit?1:0),TS(e.neg1_time),
      e.mgmt_reason,TS(e.mgmt_exit_time),DoubleToString(e.mgmt_exit_R_actual,6),F(mgmt_net_R),
      F(e.src1),F(e.src2),F(e.src3),F(e.src6),F(e.src9),
      F(e.src12),F(e.src15),F(e.src18),F(e.src24),
      F(e.exe1),F(e.exe2),F(e.exe3),F(e.exe6),F(e.exe9),
      F(e.exe12),F(e.exe15),F(e.exe18),F(e.exe24),
      F(net24),F(r24),e.terminal_reason,e.ticks_observed);
   FileFlush(g_evt_fh);
  }
// ---------------------------------------------------------------------------
void WriteControl(C1Event &e)
  {
   if(g_ctl_fh==INVALID_HANDLE) return;

   double net24=(e.exe24==EMPTY_VALUE ? EMPTY_VALUE :
                 e.exe24-e.commission_roundturn_bps);
   double r24=(e.exe24==EMPTY_VALUE || e.R_frac<=0.0 ? EMPTY_VALUE :
               (e.exe24/10000.0)/e.R_frac);

   FileWrite(g_ctl_fh,
      g_strategy,g_classification,g_cohort,_Symbol,"CONTROL_DOWNTREND_NO_DOJI",e.id,
      TS(e.signal_end),TS(e.exec_entry_time),TS(e.finish_time),
      DoubleToString(e.source_entry,_Digits),DoubleToString(e.exec_entry,_Digits),
      DoubleToString(e.sigma24,8),DoubleToString(e.R_frac,8),
      DoubleToString(e.entry_spread_points,2),DoubleToString(e.commission_roundturn_bps,4),
      (e.feed_gap?1:0),e.missing_horizons,
      F(e.src1),F(e.src2),F(e.src3),F(e.src6),F(e.src9),
      F(e.src12),F(e.src15),F(e.src18),F(e.src24),
      F(e.exe1),F(e.exe2),F(e.exe3),F(e.exe6),F(e.exe9),
      F(e.exe12),F(e.exe15),F(e.exe18),F(e.exe24),
      F(net24),F(r24),e.terminal_reason);
   FileFlush(g_ctl_fh);
  }
// ---------------------------------------------------------------------------
void CompleteEvent(int i,string reason,datetime now)
  {
   if(!g_events[i].active) return;
   g_events[i].active=false;
   g_events[i].finish_time=now;
   g_events[i].terminal_reason=reason;
   g_events[i].missing_horizons=MissingHorizonCount(g_events[i]);

   if(g_events[i].missing_horizons>0) g_events[i].feed_gap=true;

   // If no -1R/+3R first touch occurred, secondary policy times out at +24h.
   if(!g_events[i].mgmt_done && g_events[i].h24 && g_events[i].R_frac>0.0)
     {
      g_events[i].mgmt_done=true;
      g_events[i].mgmt_reason="TIMEOUT_24H";
      g_events[i].mgmt_exit_time=now;
      g_events[i].mgmt_exit_R_actual=(g_events[i].exe24/10000.0)/g_events[i].R_frac;
     }

   g_events_complete++;
   if(g_events[i].feed_gap) g_events_feedgap++;

   bool clean=(g_events[i].feed_gap==false &&
               g_events[i].missing_horizons==0 &&
               g_events[i].exe24!=EMPTY_VALUE &&
               g_events[i].R_frac>0.0);

   if(clean)
     {
      g_events_clean24++;
      double net24=g_events[i].exe24-g_events[i].commission_roundturn_bps;
      double r24=(g_events[i].exe24/10000.0)/g_events[i].R_frac;
      g_sum_exec24_bps+=g_events[i].exe24;
      g_sum_net24_bps+=net24;
      g_sum_exec24_R+=r24;
      if(net24>0.0) g_exec24_positive++;

      if(g_events[i].mgmt_done)
        {
         double mgmt_net_r=g_events[i].mgmt_exit_R_actual-
                           (g_events[i].commission_roundturn_bps/10000.0)/g_events[i].R_frac;
         g_sum_mgmt_R+=mgmt_net_r;
         if(g_events[i].mgmt_reason=="STOP_-1R_FIRST") g_mgmt_stop++;
         else if(g_events[i].mgmt_reason=="TARGET_3R_FIRST") g_mgmt_target++;
         else if(g_events[i].mgmt_reason=="TIMEOUT_24H") g_mgmt_timeout++;
        }
     }

   WriteEvent(g_events[i]);
  }
// ---------------------------------------------------------------------------
void CompleteControl(int i,string reason,datetime now)
  {
   if(!g_controls[i].active) return;
   g_controls[i].active=false;
   g_controls[i].finish_time=now;
   g_controls[i].terminal_reason=reason;
   g_controls[i].missing_horizons=MissingHorizonCount(g_controls[i]);
   if(g_controls[i].missing_horizons>0) g_controls[i].feed_gap=true;

   g_controls_complete++;
   if(!g_controls[i].feed_gap &&
      g_controls[i].missing_horizons==0 &&
      g_controls[i].exe24!=EMPTY_VALUE)
      g_controls_clean24++;

   WriteControl(g_controls[i]);
  }
// ---------------------------------------------------------------------------
void AdvanceActiveStarts()
  {
   int ne=ArraySize(g_events);
   while(g_event_active_start<ne && !g_events[g_event_active_start].active)
      g_event_active_start++;

   int nc=ArraySize(g_controls);
   while(g_control_active_start<nc && !g_controls[g_control_active_start].active)
      g_control_active_start++;
  }
// ---------------------------------------------------------------------------
void FillHorizonsEvents(datetime current_h1_open,double closed_close)
  {
   int n=ArraySize(g_events);
   double exit_bid=ExecExitPrice();

   for(int i=g_event_active_start;i<n;i++)
     {
      if(!g_events[i].active) continue;

      long delta=(long)(current_h1_open-g_events[i].signal_end);
      if(delta<=0) continue;

      if((delta%3600)!=0)
        {
         g_events[i].feed_gap=true;
         continue;
        }

      int h=(int)(delta/3600);
      if(HorizonWanted(h))
        {
         double src=DirectionalBps(g_events[i].source_entry,closed_close);
         double exe=DirectionalBps(g_events[i].exec_entry,exit_bid);
         SetHorizon(g_events[i],h,src,exe);
        }

      if(h>=C1_MAX_HOURS)
         CompleteEvent(i,"24H_COMPLETE",current_h1_open);
     }
  }
// ---------------------------------------------------------------------------
void FillHorizonsControls(datetime current_h1_open,double closed_close)
  {
   int n=ArraySize(g_controls);
   double exit_bid=ExecExitPrice();

   for(int i=g_control_active_start;i<n;i++)
     {
      if(!g_controls[i].active) continue;

      long delta=(long)(current_h1_open-g_controls[i].signal_end);
      if(delta<=0) continue;

      if((delta%3600)!=0)
        {
         g_controls[i].feed_gap=true;
         continue;
        }

      int h=(int)(delta/3600);
      if(HorizonWanted(h))
        {
         double src=DirectionalBps(g_controls[i].source_entry,closed_close);
         double exe=DirectionalBps(g_controls[i].exec_entry,exit_bid);
         SetHorizon(g_controls[i],h,src,exe);
        }

      if(h>=C1_MAX_HOURS)
         CompleteControl(i,"24H_COMPLETE",current_h1_open);
     }
  }
// ---------------------------------------------------------------------------
void ProcessClosedH1(datetime current_h1_open)
  {
   MqlRates closed;
   if(!GetH1(1,closed)) return;

   // First finish/update all events for which this bar is a future horizon.
   FillHorizonsEvents(current_h1_open,closed.close);
   FillHorizonsControls(current_h1_open,closed.close);
   AdvanceActiveStarts();

   if(Bars(_Symbol,PERIOD_H1)<C1_TREND_MA_HOURS+20) return;

   bool down=QualifyingDowntrend();
   if(!down) return;

   double sigma=Sigma24();
   if(sigma<=0.0 || !MathIsValidNumber(sigma)) return;

   bool doji=BullishDojiStar();
   g_signals_seen++;

   datetime signal_end=current_h1_open;

   if(signal_end<g_confirm_start)
     {
      g_signals_before_window++;
      return;
     }
   if(signal_end>g_confirm_last_signal)
     {
      g_signals_after_window++;
      return;
     }

   if(doji)
     {
      int n=ArraySize(g_events);
      ArrayResize(g_events,n+1);
      InitEvent(g_events[n],false,"DOJI_STAR_BULLISH",
                signal_end,closed.close,sigma,current_h1_open,g_next_event_id++);
      g_signals_accepted++;
      Print("D032-C1 CONFIRM SIGNAL | ",_Symbol,
            " | ",g_cohort," | ",TS(signal_end));
     }
   else if(InpWriteControlPool)
     {
      int n=ArraySize(g_controls);
      ArrayResize(g_controls,n+1);
      InitEvent(g_controls[n],true,"CONTROL_DOWNTREND_NO_DOJI",
                signal_end,closed.close,sigma,current_h1_open,g_next_control_id++);
     }
  }
// ---------------------------------------------------------------------------
void WriteSummary()
  {
   if(g_sum_fh==INVALID_HANDLE) return;
   double n=(double)g_events_clean24;

   FileWrite(g_sum_fh,
      g_strategy,g_cohort,_Symbol,g_signals_seen,g_signals_accepted,
      g_events_complete,g_events_clean24,g_events_feedgap,
      DoubleToString(n>0?g_sum_exec24_bps/n:0.0,6),
      DoubleToString(n>0?g_sum_net24_bps/n:0.0,6),
      DoubleToString(n>0?g_sum_exec24_R/n:0.0,6),
      DoubleToString(n>0?100.0*g_exec24_positive/n:0.0,3),
      DoubleToString(n>0?g_sum_mgmt_R/n:0.0,6),
      g_mgmt_stop,g_mgmt_target,g_mgmt_timeout,
      g_controls_complete,g_controls_clean24);
   FileFlush(g_sum_fh);
  }
// ---------------------------------------------------------------------------
int OnInit()
  {
   ArrayResize(g_events,0);
   ArrayResize(g_controls,0);
   g_cohort=DetectCohort();

   Print("D032-C1 INIT | ",_Symbol," | cohort=",g_cohort,
         " | confirmation signals ONLY ",
         TS(g_confirm_start)," -> ",TS(g_confirm_last_signal),
         " | NO ORDERS | Guardian OFF");
   return INIT_SUCCEEDED;
  }
// ---------------------------------------------------------------------------
void OnTick()
  {
   datetime now=TimeCurrent();
   if(now<=0) return;

   if(g_first_tick==0)
     {
      g_first_tick=now;
      if(!EnsureOutput(now))
        {
         Print("D032-C1 FATAL: output initialization/QA failed.");
         ExpertRemove();
         return;
        }
     }

   g_last_tick=now;
   UpdatePatternPaths(now);

   datetime h1open=iTime(_Symbol,PERIOD_H1,0);
   if(h1open<=0) return;

   if(g_last_h1_open==0)
     {
      g_last_h1_open=h1open;
      return;
     }

   if(h1open!=g_last_h1_open)
     {
      if(h1open-g_last_h1_open!=3600)
        {
         for(int i=g_event_active_start;i<ArraySize(g_events);i++)
            if(g_events[i].active) g_events[i].feed_gap=true;
         for(int i=g_control_active_start;i<ArraySize(g_controls);i++)
            if(g_controls[i].active) g_controls[i].feed_gap=true;
        }

      g_last_h1_open=h1open;
      ProcessClosedH1(h1open);
     }
  }
// ---------------------------------------------------------------------------
void OnDeinit(const int reason)
  {
   datetime now=(g_last_tick>0 ? g_last_tick : TimeCurrent());

   // Open events at tester end remain explicit; they are NOT treated as clean 24h.
   for(int i=g_event_active_start;i<ArraySize(g_events);i++)
      if(g_events[i].active) CompleteEvent(i,"EOT_INCOMPLETE",now);

   for(int i=g_control_active_start;i<ArraySize(g_controls);i++)
      if(g_controls[i].active) CompleteControl(i,"EOT_INCOMPLETE",now);

   WriteSummary();

   if(g_info_fh!=INVALID_HANDLE)
     {
      FileWrite(g_info_fh,"last_tick_server",TS(g_last_tick));
      FileWrite(g_info_fh,"signals_seen_qualifying_downtrend",IntegerToString(g_signals_seen));
      FileWrite(g_info_fh,"signals_accepted_doji",IntegerToString(g_signals_accepted));
      FileWrite(g_info_fh,"qualifying_hours_before_window",IntegerToString(g_signals_before_window));
      FileWrite(g_info_fh,"qualifying_hours_after_window",IntegerToString(g_signals_after_window));
      FileWrite(g_info_fh,"events_clean24",IntegerToString(g_events_clean24));
      FileWrite(g_info_fh,"controls_clean24",IntegerToString(g_controls_clean24));
      FileWrite(g_info_fh,"deinit_reason",IntegerToString(reason));
      FileFlush(g_info_fh);
      FileClose(g_info_fh);
      g_info_fh=INVALID_HANDLE;
     }

   if(g_evt_fh!=INVALID_HANDLE){FileFlush(g_evt_fh);FileClose(g_evt_fh);g_evt_fh=INVALID_HANDLE;}
   if(g_ctl_fh!=INVALID_HANDLE){FileFlush(g_ctl_fh);FileClose(g_ctl_fh);g_ctl_fh=INVALID_HANDLE;}
   if(g_sum_fh!=INVALID_HANDLE){FileFlush(g_sum_fh);FileClose(g_sum_fh);g_sum_fh=INVALID_HANDLE;}

   Print("D032-C1 SUMMARY | symbol=",_Symbol,
         " | cohort=",g_cohort,
         " | accepted=",g_signals_accepted,
         " | clean24=",g_events_clean24,
         " | folder=FILE_COMMON\\",g_folder);
  }
// ============================================================================