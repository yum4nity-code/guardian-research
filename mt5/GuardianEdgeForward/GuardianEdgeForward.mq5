#property strict
#property version   "100.10"
#property description "Guardian Edge Forward - frozen rank 7/9 SHADOW logger"
#property description "No order-sending code. Hard-disabled until post-2026 release window."
#property description "Requires an exact post-2026 state seed before initialization."

// Jan 2 is deliberately later than the research 2026 calendar boundary.
// The real gate is stricter still: a valid post-release seed is mandatory.
#define ACTIVATION_NOT_BEFORE D'2027.01.02 00:00'
#define MIN_SEED_N 5000
#define MAX_CATCHUP_STEPS 150000

const string EA_NAME="GuardianEdgeForward";
const string SYM_DXY="DXY.cash";
const string SYM_USDJPY="USDJPY";
const string SYM_USDCHF="USDCHF";
const string SYM_XAUUSD="XAUUSD";
const string SYM_GBPUSD="GBPUSD";

input string SeedFile="GuardianEdgeForward\\state_seed_v100.csv";
input string RuntimeStateFile="GuardianEdgeForward\\runtime_state_v100.csv";
input string ShadowLogFile="GuardianEdgeForward\\shadow_signals_v100.csv";
input int    TargetFreshnessSeconds=180;

enum FeatureKind
  {
   FK_RET30=0,
   FK_RV60=1,
   FK_ZRET60=2
  };

enum FeatureSlot
  {
   FS_USDJPY_ZRET60=0,
   FS_USDCHF_RV60=1,
   FS_XAUUSD_RV60=2,
   FS_GBPUSD_RET30=3,
   FS_COUNT=4
  };

struct RunningStat
  {
   long n;
   double sum;
   double sumsq;
  };

struct FeatureSnapshot
  {
   datetime decision_time;
   double value;
   double prior_mean;
   double prior_std;
   bool lo;
   bool hi;
   bool finite;
  };

RunningStat g_stats[FS_COUNT];
FeatureSnapshot g_snap[FS_COUNT];
datetime g_last_decision_time=0;

string FeatureName(const int slot)
  {
   if(slot==FS_USDJPY_ZRET60) return "price_USDJPY_zret_60m";
   if(slot==FS_USDCHF_RV60) return "price_USDCHF_rv_60m";
   if(slot==FS_XAUUSD_RV60) return "price_XAUUSD_rv_60m";
   if(slot==FS_GBPUSD_RET30) return "price_GBPUSD_ret_30m";
   return "UNKNOWN";
  }

int FeatureSlotFromName(const string name)
  {
   for(int i=0;i<FS_COUNT;i++)
      if(name==FeatureName(i)) return i;
   return -1;
  }

bool IsFiniteNumber(const double x)
  {
   return MathIsValidNumber(x) && x!=DBL_MAX && x!=-DBL_MAX;
  }

double SampleStd(const RunningStat &s)
  {
   if(s.n<2) return 0.0;
   double numerator=s.sumsq-(s.sum*s.sum)/(double)s.n;
   if(numerator<0.0 && MathAbs(numerator)<1e-18) numerator=0.0;
   if(numerator<=0.0) return 0.0;
   return MathSqrt(numerator/(double)(s.n-1));
  }

void UpdateStat(RunningStat &s,const double x)
  {
   s.n++;
   s.sum+=x;
   s.sumsq+=x*x;
  }

bool EnsureSymbol(const string sym)
  {
   if(!SymbolSelect(sym,true))
     {
      Print(EA_NAME,": cannot select symbol ",sym," error=",GetLastError());
      return false;
     }
   return true;
  }

int ExactBarShiftForDecision(const string sym,const datetime decision_time)
  {
   datetime bar_open=decision_time-300;
   int shift=iBarShift(sym,PERIOD_M5,bar_open,true);
   if(shift<0) return -1;
   if(iTime(sym,PERIOD_M5,shift)!=bar_open) return -1;
   return shift;
  }

bool ContinuousM5WindowAtShift(const string sym,const int newest_shift,const int intervals)
  {
   datetime newest=iTime(sym,PERIOD_M5,newest_shift);
   if(newest<=0) return false;
   for(int j=1;j<=intervals;j++)
     {
      datetime older=iTime(sym,PERIOD_M5,newest_shift+j);
      if(older<=0) return false;
      if(older!=(newest-j*300)) return false;
     }
   return true;
  }

bool ComputeRet30At(const string sym,const datetime decision_time,double &out)
  {
   int sh=ExactBarShiftForDecision(sym,decision_time);
   if(sh<0 || !ContinuousM5WindowAtShift(sym,sh,6)) return false;
   double c0=iClose(sym,PERIOD_M5,sh);
   double c6=iClose(sym,PERIOD_M5,sh+6);
   if(c0<=0.0 || c6<=0.0) return false;
   out=c0/c6-1.0;
   return IsFiniteNumber(out);
  }

bool Build12R5At(const string sym,const datetime decision_time,double &r[])
  {
   int sh0=ExactBarShiftForDecision(sym,decision_time);
   if(sh0<0 || !ContinuousM5WindowAtShift(sym,sh0,12)) return false;
   ArrayResize(r,12);
   for(int i=0;i<12;i++)
     {
      int sh=sh0+i;
      double c0=iClose(sym,PERIOD_M5,sh);
      double c1=iClose(sym,PERIOD_M5,sh+1);
      if(c0<=0.0 || c1<=0.0) return false;
      r[i]=c0/c1-1.0;
      if(!IsFiniteNumber(r[i])) return false;
     }
   return true;
  }

bool MeanStd12(const double &r[],double &mean,double &sd)
  {
   if(ArraySize(r)!=12) return false;
   double sum=0.0;
   double ss=0.0;
   for(int i=0;i<12;i++)
     {
      sum+=r[i];
      ss+=r[i]*r[i];
     }
   mean=sum/12.0;
   double numerator=ss-(sum*sum)/12.0;
   if(numerator<0.0 && MathAbs(numerator)<1e-18) numerator=0.0;
   if(numerator<=0.0) return false;
   sd=MathSqrt(numerator/11.0);
   return IsFiniteNumber(mean) && IsFiniteNumber(sd) && sd>0.0;
  }

bool ComputeRv60At(const string sym,const datetime decision_time,double &out)
  {
   double r[];
   if(!Build12R5At(sym,decision_time,r)) return false;
   double mean=0.0,sd=0.0;
   if(!MeanStd12(r,mean,sd)) return false;
   out=sd;
   return IsFiniteNumber(out);
  }

bool ComputeZret60At(const string sym,const datetime decision_time,double &out)
  {
   double r[];
   if(!Build12R5At(sym,decision_time,r)) return false;
   double mean=0.0,sd=0.0;
   if(!MeanStd12(r,mean,sd)) return false;
   out=(r[0]-mean)/sd;
   return IsFiniteNumber(out);
  }

bool ComputeFeatureAt(const string sym,const FeatureKind kind,const datetime decision_time,double &out)
  {
   if(kind==FK_RET30) return ComputeRet30At(sym,decision_time,out);
   if(kind==FK_RV60) return ComputeRv60At(sym,decision_time,out);
   if(kind==FK_ZRET60) return ComputeZret60At(sym,decision_time,out);
   return false;
  }

bool LoadStateFile(const string filename,const bool seed_file)
  {
   int h=FileOpen(filename,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE) return false;

   bool seen[FS_COUNT];
   for(int i=0;i<FS_COUNT;i++) seen[i]=false;
   datetime common_time=0;

   while(!FileIsEnding(h))
     {
      string name=FileReadString(h);
      if(name=="") continue;
      string ns=FileReadString(h);
      string sums=FileReadString(h);
      string sss=FileReadString(h);
      string times=FileReadString(h);
      if(name=="feature" || name=="FEATURE") continue;

      int slot=FeatureSlotFromName(name);
      if(slot<0)
        {
         Print(EA_NAME,": unknown state feature ",name," in ",filename);
         FileClose(h);
         return false;
        }

      long n=(long)StringToInteger(ns);
      double sum=StringToDouble(sums);
      double sumsq=StringToDouble(sss);
      datetime last_time=StringToTime(times);
      if(n<MIN_SEED_N || !IsFiniteNumber(sum) || !IsFiniteNumber(sumsq) || sumsq<=0.0 || last_time<=0)
        {
         Print(EA_NAME,": invalid state row ",name," in ",filename);
         FileClose(h);
         return false;
        }
      if(common_time==0) common_time=last_time;
      if(last_time!=common_time)
        {
         Print(EA_NAME,": inconsistent last_decision_time in ",filename);
         FileClose(h);
         return false;
        }

      g_stats[slot].n=n;
      g_stats[slot].sum=sum;
      g_stats[slot].sumsq=sumsq;
      seen[slot]=true;
     }
   FileClose(h);

   for(int i=0;i<FS_COUNT;i++)
      if(!seen[i]) return false;

   // A seed is allowed to predate the activation floor because it covers the
   // released research history. Runtime state must never predate the seed.
   if(seed_file && common_time>=ACTIVATION_NOT_BEFORE)
     {
      // This is not fatal scientifically, but it is suspicious enough to stop:
      // the seed generator should explicitly document the released cutoff.
      Print(EA_NAME,": seed cutoff must be before activation floor; got ",
            TimeToString(common_time,TIME_DATE|TIME_MINUTES));
      return false;
     }

   g_last_decision_time=common_time;
   return true;
  }

bool SaveRuntimeState()
  {
   int h=FileOpen(RuntimeStateFile,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)
     {
      Print(EA_NAME,": cannot persist runtime state error=",GetLastError());
      return false;
     }
   FileWrite(h,"feature","n","sum","sumsq","last_decision_time");
   for(int i=0;i<FS_COUNT;i++)
      FileWrite(h,
                FeatureName(i),
                g_stats[i].n,
                DoubleToString(g_stats[i].sum,16),
                DoubleToString(g_stats[i].sumsq,16),
                TimeToString(g_last_decision_time,TIME_DATE|TIME_MINUTES|TIME_SECONDS));
   FileFlush(h);
   FileClose(h);
   return true;
  }

bool LoadInitialState()
  {
   if(FileIsExist(RuntimeStateFile,FILE_COMMON))
     {
      if(!LoadStateFile(RuntimeStateFile,false))
        {
         Print(EA_NAME,": runtime state exists but is invalid; refusing seed fallback.");
         return false;
        }
      Print(EA_NAME,": resumed runtime state at ",
            TimeToString(g_last_decision_time,TIME_DATE|TIME_MINUTES));
      return true;
     }

   if(!FileIsExist(SeedFile,FILE_COMMON))
     {
      Print(EA_NAME,": seed file missing: ",SeedFile,
            ". Intentional until protected 2026 is released and exact FTMO-continuation seed is generated.");
      return false;
     }
   if(!LoadStateFile(SeedFile,true))
     {
      Print(EA_NAME,": seed file exists but is invalid.");
      return false;
     }
   Print(EA_NAME,": loaded post-release seed cutoff ",
         TimeToString(g_last_decision_time,TIME_DATE|TIME_MINUTES));
   return true;
  }

void ResetSnapshotsForDecision(const datetime t)
  {
   for(int i=0;i<FS_COUNT;i++)
     {
      g_snap[i].decision_time=t;
      g_snap[i].value=0.0;
      g_snap[i].prior_mean=0.0;
      g_snap[i].prior_std=0.0;
      g_snap[i].lo=false;
      g_snap[i].hi=false;
      g_snap[i].finite=false;
     }
  }

void ProcessFeatureAtDecision(const int slot,const string sym,const FeatureKind kind,const datetime t)
  {
   double value=0.0;
   if(!ComputeFeatureAt(sym,kind,t,value)) return;

   RunningStat prior=g_stats[slot];
   if(prior.n<MIN_SEED_N) return;
   double mean=prior.sum/(double)prior.n;
   double sd=SampleStd(prior);
   if(!IsFiniteNumber(mean) || !IsFiniteNumber(sd) || sd<=0.0) return;

   g_snap[slot].value=value;
   g_snap[slot].prior_mean=mean;
   g_snap[slot].prior_std=sd;
   g_snap[slot].lo=(value<=mean-sd);
   g_snap[slot].hi=(value>=mean+sd);
   g_snap[slot].finite=true;

   // Exact causal order: state on prior stats, then append current feature.
   UpdateStat(g_stats[slot],value);
  }

bool IsDecisionBoundary(const datetime t,const int horizon_min)
  {
   MqlDateTime dt;
   TimeToStruct(t,dt);
   int minute_of_day=dt.hour*60+dt.min;
   return (minute_of_day%horizon_min)==0;
  }

bool FreshTargetTick(const string sym)
  {
   MqlTick tick;
   if(!SymbolInfoTick(sym,tick)) return false;
   if(tick.time<=0) return false;
   long age=(long)(TimeCurrent()-tick.time);
   if(age<0) age=-age;
   return age<=TargetFreshnessSeconds;
  }

void WriteSignal(const int rank,
                 const datetime decision_time,
                 const string target,
                 const string direction,
                 const int horizon,
                 const FeatureSnapshot &a,
                 const FeatureSnapshot &b,
                 const bool target_fresh,
                 const bool replayed)
  {
   int h=FileOpen(ShadowLogFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)
     {
      Print(EA_NAME,": cannot open shadow log ",ShadowLogFile," error=",GetLastError());
      return;
     }

   bool empty=(FileSize(h)==0);
   FileSeek(h,0,SEEK_END);
   if(empty)
      FileWrite(h,
                "ea_version","rank","decision_server_time","target","direction","horizon_min",
                "feature_a","a_value","a_prior_mean","a_prior_std","a_lo","a_hi",
                "feature_b","b_value","b_prior_mean","b_prior_std","b_lo","b_hi",
                "target_tick_fresh","replayed","shadow_only");

   string fa=(rank==7 ? FeatureName(FS_USDJPY_ZRET60) : FeatureName(FS_XAUUSD_RV60));
   string fb=(rank==7 ? FeatureName(FS_USDCHF_RV60) : FeatureName(FS_GBPUSD_RET30));

   FileWrite(h,
             "V100.10",
             rank,
             TimeToString(decision_time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
             target,
             direction,
             horizon,
             fa,DoubleToString(a.value,12),DoubleToString(a.prior_mean,12),DoubleToString(a.prior_std,12),a.lo,a.hi,
             fb,DoubleToString(b.value,12),DoubleToString(b.prior_mean,12),DoubleToString(b.prior_std,12),b.lo,b.hi,
             target_fresh,
             replayed,
             true);
   FileFlush(h);
   FileClose(h);
  }

void EvaluateSignalsAtDecision(const datetime t,const bool allow_signal,const bool replayed)
  {
   if(!allow_signal) return;

   FeatureSnapshot a7=g_snap[FS_USDJPY_ZRET60];
   FeatureSnapshot b7=g_snap[FS_USDCHF_RV60];
   if(IsDecisionBoundary(t,15) && a7.finite && b7.finite && a7.lo && b7.hi)
      WriteSignal(7,t,SYM_DXY,"LONG",15,a7,b7,(replayed ? false : FreshTargetTick(SYM_DXY)),replayed);

   FeatureSnapshot a9=g_snap[FS_XAUUSD_RV60];
   FeatureSnapshot b9=g_snap[FS_GBPUSD_RET30];
   if(IsDecisionBoundary(t,30) && a9.finite && b9.finite && a9.hi && b9.hi)
      WriteSignal(9,t,SYM_GBPUSD,"SHORT",30,a9,b9,(replayed ? false : FreshTargetTick(SYM_GBPUSD)),replayed);
  }

bool ProcessDecision(const datetime t,const datetime latest_decision)
  {
   ResetSnapshotsForDecision(t);

   ProcessFeatureAtDecision(FS_USDJPY_ZRET60,SYM_USDJPY,FK_ZRET60,t);
   ProcessFeatureAtDecision(FS_USDCHF_RV60,SYM_USDCHF,FK_RV60,t);
   ProcessFeatureAtDecision(FS_XAUUSD_RV60,SYM_XAUUSD,FK_RV60,t);
   ProcessFeatureAtDecision(FS_GBPUSD_RET30,SYM_GBPUSD,FK_RET30,t);

   bool allow_signal=(t>=ACTIVATION_NOT_BEFORE);
   bool replayed=(t<latest_decision);
   EvaluateSignalsAtDecision(t,allow_signal,replayed);

   g_last_decision_time=t;
   return SaveRuntimeState();
  }

datetime LatestCompletedDecisionTime()
  {
   datetime now=TimeCurrent();
   if(now<=0) return 0;
   long x=(long)now;
   return (datetime)((x/300)*300);
  }

bool CatchUpToLatest()
  {
   datetime latest=LatestCompletedDecisionTime();
   if(latest<=0) return false;
   if(g_last_decision_time>=latest) return true;

   long steps=(long)((latest-g_last_decision_time)/300);
   if(steps>MAX_CATCHUP_STEPS)
     {
      Print(EA_NAME,": catch-up gap too large (",steps,
            " M5 decisions). Regenerate an audited state seed instead of silently skipping history.");
      return false;
     }

   for(datetime t=g_last_decision_time+300;t<=latest;t+=300)
     {
      if(!ProcessDecision(t,latest)) return false;
     }
   return true;
  }

int OnInit()
  {
   // Absolute protection of the untouched 2026 research OOS.
   if(TimeCurrent()<ACTIVATION_NOT_BEFORE)
     {
      Print(EA_NAME,": HARD LOCK active until ",
            TimeToString(ACTIVATION_NOT_BEFORE,TIME_DATE|TIME_MINUTES),
            ". No feature calculation or signal logging.");
      return INIT_FAILED;
     }

   if(!EnsureSymbol(SYM_DXY) ||
      !EnsureSymbol(SYM_USDJPY) ||
      !EnsureSymbol(SYM_USDCHF) ||
      !EnsureSymbol(SYM_XAUUSD) ||
      !EnsureSymbol(SYM_GBPUSD))
      return INIT_FAILED;

   if(!LoadInitialState()) return INIT_FAILED;
   if(!CatchUpToLatest()) return INIT_FAILED;

   EventSetTimer(1);
   Print(EA_NAME,": initialized in SHADOW-ONLY mode. No order-sending code is present.");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

void OnTimer()
  {
   if(TimeCurrent()<ACTIVATION_NOT_BEFORE) return;
   if(!CatchUpToLatest())
      Print(EA_NAME,": catch-up failed; shadow state not advanced.");
  }
