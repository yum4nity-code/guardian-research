#property strict
#property version   "1.00"
#property description "R18 XAUUSD M5 MVP EA. Frozen shock logic, time exit, dry-run default."

#include <Trade/Trade.mqh>

input string InpSymbol = "XAUUSD";
input double InpShockThreshold = 2.0;
input int    InpLookback = 48;
input int    InpExitBars = 1;              // allowed: 1,2,4,8,16
input double InpLots = 0.01;
input bool   InpEnableTrading = false;      // SAFETY: false by default
input long   InpMagic = 180018;
input int    InpMaxDeviationPoints = 30;
input double InpMaxSpreadBps = 0.0;         // 0 = disabled; filtering changes execution sample
input string InpLogFile = "R18_XAUUSD_EA_MVP_v1_00.csv";

CTrade trade;
datetime g_last_bar0 = 0;
datetime g_entry_bar_time = 0;
int g_log = INVALID_HANDLE;

bool IsAllowedExitBars(const int x)
{
   return (x==1 || x==2 || x==4 || x==8 || x==16);
}

bool IsOurPosition()
{
   if(!PositionSelect(InpSymbol)) return false;
   long magic = (long)PositionGetInteger(POSITION_MAGIC);
   return (magic == InpMagic);
}

void LogLine(const string event_name,const string detail)
{
   if(g_log==INVALID_HANDLE) return;
   FileWrite(g_log,
      TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
      event_name,
      detail);
   FileFlush(g_log);
}

double MidPrice()
{
   MqlTick t;
   if(!SymbolInfoTick(InpSymbol,t)) return 0.0;
   if(t.bid<=0.0 || t.ask<=0.0) return 0.0;
   return (t.bid+t.ask)*0.5;
}

double SpreadBps()
{
   MqlTick t;
   if(!SymbolInfoTick(InpSymbol,t)) return 0.0;
   double m=(t.bid+t.ask)*0.5;
   if(m<=0.0) return 0.0;
   return (t.ask-t.bid)/m*10000.0;
}

bool LoadClosedBars(MqlRates &rates[],const int count)
{
   ArraySetAsSeries(rates,true);
   ResetLastError();
   int copied=CopyRates(InpSymbol,PERIOD_M5,1,count,rates);
   if(copied!=count)
   {
      Print("R18 EA CopyRates failed copied=",copied," need=",count," err=",GetLastError());
      return false;
   }
   return true;
}

bool ComputeShock(double &bar_return,double &shock_score,int &shock_direction)
{
   if(InpLookback<2) return false;
   const int need=InpLookback+2;
   MqlRates r[];
   if(!LoadClosedBars(r,need)) return false;

   // r[0] = just-closed shock candidate, r[1] = previous closed bar.
   if(r[1].close<=0.0 || r[0].close<=0.0) return false;
   bar_return=r[0].close/r[1].close-1.0;

   // Frozen definition: sample stdev of previous 48 contiguous close-to-close returns,
   // excluding current candidate return. Hist returns are between r[1]..r[InpLookback+1].
   double vals[];
   ArrayResize(vals,InpLookback);
   double sum=0.0;
   for(int k=0;k<InpLookback;k++)
   {
      datetime newer=r[k+1].time;
      datetime older=r[k+2].time;
      if(newer-older!=300) return false;
      if(r[k+2].close<=0.0 || r[k+1].close<=0.0) return false;
      double x=r[k+1].close/r[k+2].close-1.0;
      vals[k]=x;
      sum+=x;
   }

   double mean=sum/InpLookback;
   double ss=0.0;
   for(int k=0;k<InpLookback;k++)
   {
      double d=vals[k]-mean;
      ss+=d*d;
   }
   double sd=MathSqrt(ss/(InpLookback-1));
   if(sd<=0.0) return false;

   shock_score=MathAbs(bar_return)/sd;
   shock_direction=(bar_return>0.0 ? 1 : (bar_return<0.0 ? -1 : 0));
   return (shock_direction!=0);
}

bool OpenContrarian(const int shock_direction,const double score,const double bar_return)
{
   double sp=SpreadBps();
   if(InpMaxSpreadBps>0.0 && sp>InpMaxSpreadBps)
   {
      LogLine("SKIP_SPREAD",StringFormat("score=%.6f ret=%.10f spread_bps=%.6f",score,bar_return,sp));
      return false;
   }

   string side=(shock_direction>0 ? "SELL" : "BUY");
   LogLine("SIGNAL",StringFormat("side=%s score=%.6f ret=%.10f spread_bps=%.6f",side,score,bar_return,sp));

   if(!InpEnableTrading)
   {
      Print("R18 SIGNAL DRY-RUN ",side," score=",DoubleToString(score,4));
      return true;
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);

   bool ok=false;
   if(shock_direction>0)
      ok=trade.Sell(InpLots,InpSymbol,0.0,0.0,0.0,"R18 contrarian");
   else
      ok=trade.Buy(InpLots,InpSymbol,0.0,0.0,0.0,"R18 contrarian");

   if(!ok)
   {
      Print("R18 order failed retcode=",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      LogLine("ORDER_FAIL",StringFormat("retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription()));
      return false;
   }

   g_entry_bar_time=iTime(InpSymbol,PERIOD_M5,0);
   LogLine("OPEN",StringFormat("side=%s lots=%.4f price=%.5f",side,InpLots,trade.ResultPrice()));
   return true;
}

void TryTimedExit()
{
   if(!InpEnableTrading) return;
   if(!IsOurPosition()) return;
   if(g_entry_bar_time<=0) return;

   datetime bar0=iTime(InpSymbol,PERIOD_M5,0);
   if(bar0<=0) return;
   int bars_elapsed=(int)((bar0-g_entry_bar_time)/300);
   if(bars_elapsed<InpExitBars) return;

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(trade.PositionClose(InpSymbol,InpMaxDeviationPoints))
   {
      LogLine("CLOSE",StringFormat("bars_elapsed=%d price=%.5f",bars_elapsed,trade.ResultPrice()));
      g_entry_bar_time=0;
   }
   else
   {
      Print("R18 close failed retcode=",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      LogLine("CLOSE_FAIL",StringFormat("retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription()));
   }
}

int OnInit()
{
   if(_Symbol!=InpSymbol)
   {
      Print("Attach to exact symbol ",InpSymbol,". Current chart=",_Symbol);
      return INIT_FAILED;
   }
   if(_Period!=PERIOD_M5)
   {
      Print("Attach to M5 chart only.");
      return INIT_FAILED;
   }
   if(InpShockThreshold<=0.0 || InpLookback<2 || InpLots<=0.0 || !IsAllowedExitBars(InpExitBars))
   {
      Print("Invalid inputs. ExitBars must be one of 1,2,4,8,16.");
      return INIT_PARAMETERS_INCORRECT;
   }

   g_log=FileOpen(InpLogFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',');
   if(g_log!=INVALID_HANDLE)
   {
      if(FileSize(g_log)==0) FileWrite(g_log,"time_server","event","detail");
      FileSeek(g_log,0,SEEK_END);
      FileFlush(g_log);
   }
   else
   {
      Print("R18 log FileOpen failed err=",GetLastError());
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   g_last_bar0=iTime(InpSymbol,PERIOD_M5,0);

   if(IsOurPosition())
   {
      datetime pt=(datetime)PositionGetInteger(POSITION_TIME);
      g_entry_bar_time=(datetime)(pt-(pt%300));
   }

   Print("R18_XAUUSD_EA_MVP_v1_00 active. Trading=",(InpEnableTrading?"ON":"OFF (dry-run)"));
   LogLine("START",InpEnableTrading?"trading_on":"dry_run");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   LogLine("STOP",StringFormat("reason=%d",reason));
   if(g_log!=INVALID_HANDLE) FileClose(g_log);
}

void OnTick()
{
   datetime bar0=iTime(InpSymbol,PERIOD_M5,0);
   if(bar0<=0 || bar0==g_last_bar0) return;

   // First tick of a new M5 bar: this is the causal next-bar execution point.
   g_last_bar0=bar0;

   TryTimedExit();
   if(IsOurPosition()) return;

   double bar_return=0.0, score=0.0;
   int shock_direction=0;
   if(!ComputeShock(bar_return,score,shock_direction)) return;
   if(score<InpShockThreshold) return;

   OpenContrarian(shock_direction,score,bar_return);
}
