#property strict
#property version   "100.00"
#property description "Guardian Edge Forward - frozen rank 7/9 SHADOW logger"
#property description "No order-sending code. Hard-disabled before 2027-01-01."
#property description "Requires an exact post-2026 state seed before initialization."

#define ACTIVATION_NOT_BEFORE D'2027.01.01 00:00'
#define MIN_SEED_N 5000

const string EA_NAME="GuardianEdgeForward";
const string SYM_DXY="DXY.cash";
const string SYM_USDJPY="USDJPY";
const string SYM_USDCHF="USDCHF";
const string SYM_XAUUSD="XAUUSD";
const string SYM_GBPUSD="GBPUSD";

input string SeedFile="GuardianEdgeForward\\state_seed_v100.csv";
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
   datetime bar_time;
   double value;
   double prior_mean;
   double prior_std;
   bool lo;
   bool hi;
   bool finite;
  };

RunningStat g_stats[FS_COUNT];
FeatureSnapshot g_snap[FS_COUNT];
datetime g_last_processed[FS_COUNT];
datetime g_last_rank7_eval=0;
datetime g_last_rank9_eval=0;

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

bool ContinuousM5Window(const string sym,const int newest_shift,const int intervals)
  {
   datetime prev=iTime(sym,PERIOD_M5,newest_shift);
   if(prev<=0) return false;
   for(int j=1;j<=intervals;j++)
     {
      datetime older=iTime(sym,PERIOD_M5,newest_shift+j);
      if(older<=0) return false;
      if((prev-older)!=300) return false;
      prev=older;
     }
   return true;
  }

bool ComputeRet30(const string sym,double &out)
  {
   if(!ContinuousM5Window(sym,1,6)) return false;
   double c0=iClose(sym,PERIOD_M5,1);
   double c6=iClose(sym,PERIOD_M5,7);
   if(c0<=0.0 || c6<=0.0) return false;
   out=c0/c6-1.0;
   return IsFiniteNumber(out);
  }

bool BuildLast12R5(const string sym,double &r[])
  {
   ArrayResize(r,12);
   if(!ContinuousM5Window(sym,1,12)) return false;
   for(int i=0;i<12;i++)
     {
      int sh=1+i;
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

bool ComputeRv60(const string sym,double &out)
  {
   double r[];
   if(!BuildLast12R5(sym,r)) return false;
   double mean=0.0,sd=0.0;
   if(!MeanStd12(r,mean,sd)) return false;
   out=sd;
   return IsFiniteNumber(out);
  }

bool ComputeZret60(const string sym,double &out)
  {
   double r[];
   if(!BuildLast12R5(sym,r)) return false;
   double mean=0.0,sd=0.0;
   if(!MeanStd12(r,mean,sd)) return false;
   out=(r[0]-mean)/sd;
   return IsFiniteNumber(out);
  }

bool ComputeFeature(const string sym,const FeatureKind kind,double &out)
  {
   if(kind==FK_RET30) return ComputeRet30(sym,out);
   if(kind==FK_RV60) return ComputeRv60(sym,out);
   if(kind==FK_ZRET60) return ComputeZret60(sym,out);
   return false;
  }

bool LoadStateSeed()
  {
   for(int i=0;i<FS_COUNT;i++)
     {
      g_stats[i].n=0;
      g_stats[i].sum=0.0;
      g_stats[i].sumsq=0.0;
     }

   int h=FileOpen(SeedFile,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)
     {
      Print(EA_NAME,": seed file missing: ",SeedFile,
            ". Intentional until protected 2026 is released and exact FTMO-continuation seed is generated.");
      return false;
     }

   bool seen[FS_COUNT];
   ArrayInitialize(seen,false);
   while(!FileIsEnding(h))
     {
      string name=FileReadString(h);
      if(name=="") continue;
      string ns=FileReadString(h);
      string sums=FileReadString(h);
      string sss=FileReadString(h);
      if(name=="feature" || name=="FEATURE") continue;

      int slot=FeatureSlotFromName(name);
      if(slot<0)
        {
         Print(EA_NAME,": unknown seed feature ",name);
         FileClose(h);
         return false;
        }

      long n=(long)StringToInteger(ns);
      double sum=StringToDouble(sums);
      double sumsq=StringToDouble(sss);
      if(n<MIN_SEED_N || !IsFiniteNumber(sum) || !IsFiniteNumber(sumsq) || sumsq<=0.0)
        {
         Print(EA_NAME,": invalid seed stats for ",name," n=",n);
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
     {
      if(!seen[i])
        {
         Print(EA_NAME,": seed missing feature ",FeatureName(i));
         return false;
        }
     }
   return true;
  }

void ResetSnapshots()
  {
   for(int i=0;i<FS_COUNT;i++)
     {
      g_last_processed[i]=0;
      g_snap[i].bar_time=0;
      g_snap[i].value=0.0;
      g_snap[i].prior_mean=0.0;
      g_snap[i].prior_std=0.0;
      g_snap[i].lo=false;
      g_snap[i].hi=false;
      g_snap[i].finite=false;
     }
  }

void ProcessFeature(const int slot,const string sym,const FeatureKind kind)
  {
   datetime t=iTime(sym,PERIOD_M5,1);
   if(t<=0 || t==g_last_processed[slot]) return;
   g_last_processed[slot]=t;

   g_snap[slot].bar_time=t;
   g_snap[slot].finite=false;
   g_snap[slot].lo=false;
   g_snap[slot].hi=false;

   double value=0.0;
   if(!ComputeFeature(sym,kind,value)) return;

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

   // causal_states evaluates current value on PRIOR expanding stats, then appends current value.
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
                 const bool target_fresh)
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
                "target_tick_fresh","shadow_only");

   string fa=(rank==7 ? FeatureName(FS_USDJPY_ZRET60) : FeatureName(FS_XAUUSD_RV60));
   string fb=(rank==7 ? FeatureName(FS_USDCHF_RV60) : FeatureName(FS_GBPUSD_RET30));

   FileWrite(h,
             "V100.00",
             rank,
             TimeToString(decision_time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
             target,
             direction,
             horizon,
             fa,DoubleToString(a.value,12),DoubleToString(a.prior_mean,12),DoubleToString(a.prior_std,12),a.lo,a.hi,
             fb,DoubleToString(b.value,12),DoubleToString(b.prior_mean,12),DoubleToString(b.prior_std,12),b.lo,b.hi,
             target_fresh,
             true);
   FileFlush(h);
   FileClose(h);

   Print(EA_NAME,": SHADOW signal rank=",rank,
         " time=",TimeToString(decision_time,TIME_DATE|TIME_MINUTES),
         " target=",target," ",direction," horizon=",horizon,
         " target_fresh=",target_fresh);
  }

void EvaluateRank7()
  {
   FeatureSnapshot a=g_snap[FS_USDJPY_ZRET60];
   FeatureSnapshot b=g_snap[FS_USDCHF_RV60];
   if(!a.finite || !b.finite) return;
   if(a.bar_time!=b.bar_time) return;
   datetime t=a.bar_time+300;
   if(t==g_last_rank7_eval) return;
   g_last_rank7_eval=t;
   if(!IsDecisionBoundary(t,15)) return;
   if(a.lo && b.hi)
      WriteSignal(7,t,SYM_DXY,"LONG",15,a,b,FreshTargetTick(SYM_DXY));
  }

void EvaluateRank9()
  {
   FeatureSnapshot a=g_snap[FS_XAUUSD_RV60];
   FeatureSnapshot b=g_snap[FS_GBPUSD_RET30];
   if(!a.finite || !b.finite) return;
   if(a.bar_time!=b.bar_time) return;
   datetime t=a.bar_time+300;
   if(t==g_last_rank9_eval) return;
   g_last_rank9_eval=t;
   if(!IsDecisionBoundary(t,30)) return;
   if(a.hi && b.hi)
      WriteSignal(9,t,SYM_GBPUSD,"SHORT",30,a,b,FreshTargetTick(SYM_GBPUSD));
  }

int OnInit()
  {
   // Absolute protection of untouched 2026 research OOS:
   // no feature calculation or signal logging before 2027.
   if(TimeCurrent()<ACTIVATION_NOT_BEFORE)
     {
      Print(EA_NAME,": HARD LOCK active. No feature calculation or signal logging before ",
            TimeToString(ACTIVATION_NOT_BEFORE,TIME_DATE|TIME_MINUTES));
      return INIT_FAILED;
     }

   if(!EnsureSymbol(SYM_DXY) ||
      !EnsureSymbol(SYM_USDJPY) ||
      !EnsureSymbol(SYM_USDCHF) ||
      !EnsureSymbol(SYM_XAUUSD) ||
      !EnsureSymbol(SYM_GBPUSD))
      return INIT_FAILED;

   if(!LoadStateSeed())
      return INIT_FAILED;

   ResetSnapshots();
   EventSetTimer(1);
   Print(EA_NAME,": initialized in SHADOW-ONLY mode. There is no order-sending code in this EA.");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

void OnTimer()
  {
   if(TimeCurrent()<ACTIVATION_NOT_BEFORE) return;

   ProcessFeature(FS_USDJPY_ZRET60,SYM_USDJPY,FK_ZRET60);
   ProcessFeature(FS_USDCHF_RV60,SYM_USDCHF,FK_RV60);
   ProcessFeature(FS_XAUUSD_RV60,SYM_XAUUSD,FK_RV60);
   ProcessFeature(FS_GBPUSD_RET30,SYM_GBPUSD,FK_RET30);

   EvaluateRank7();
   EvaluateRank9();
  }
