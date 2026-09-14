#property strict
#property version   "1.01"
#property description "R18 XAUUSD M5 MVP EA. Frozen shock logic, ticket-safe hedging management, dry-run default."

#include <Trade/Trade.mqh>

input string InpSymbol = "XAUUSD";
input double InpShockThreshold = 2.0;
input int    InpLookback = 48;
input int    InpExitBars = 1;              // allowed: 1,2,4,8,16
input double InpLots = 0.01;
input bool   InpEnableTrading = false;
input long   InpMagic = 180018;
input int    InpMaxDeviationPoints = 30;
input double InpMaxSpreadBps = 0.0;         // 0 = disabled
input string InpLogFile = "R18_XAUUSD_EA_MVP_v1_01.csv";

CTrade trade;
datetime g_last_bar0 = 0;
datetime g_entry_bar_time = 0;
ulong g_position_ticket = 0;
int g_log = INVALID_HANDLE;

bool IsAllowedExitBars(const int x){ return (x==1 || x==2 || x==4 || x==8 || x==16); }

void LogLine(const string event_name,const string detail)
{
   if(g_log==INVALID_HANDLE) return;
   FileWrite(g_log,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),event_name,detail);
   FileFlush(g_log);
}

ulong FindOurPositionTicket()
{
   ulong found=0;
   int matches=0;
   for(int i=0;i<PositionsTotal();i++)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=InpSymbol) continue;
      if((long)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      found=ticket;
      matches++;
   }
   if(matches>1)
      Print("R18 WARNING: multiple positions match symbol+magic; newest scan ticket=",found);
   return (matches>0 ? found : 0);
}

bool RefreshOurPosition()
{
   g_position_ticket=FindOurPositionTicket();
   if(g_position_ticket==0) return false;
   if(!PositionSelectByTicket(g_position_ticket)) return false;
   if(g_entry_bar_time<=0)
   {
      datetime pt=(datetime)PositionGetInteger(POSITION_TIME);
      g_entry_bar_time=(datetime)(pt-(pt%300));
   }
   return true;
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
   if(r[1].close<=0.0 || r[0].close<=0.0) return false;
   bar_return=r[0].close/r[1].close-1.0;

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

   if(FindOurPositionTicket()!=0)
   {
      LogLine("SKIP_POSITION","existing R18 position");
      return false;
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);

   bool ok=(shock_direction>0)
      ? trade.Sell(InpLots,InpSymbol,0.0,0.0,0.0,"R18 contrarian")
      : trade.Buy(InpLots,InpSymbol,0.0,0.0,0.0,"R18 contrarian");

   if(!ok)
   {
      Print("R18 order failed retcode=",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      LogLine("ORDER_FAIL",StringFormat("retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription()));
      return false;
   }

   g_position_ticket=FindOurPositionTicket();
   g_entry_bar_time=iTime(InpSymbol,PERIOD_M5,0);
   LogLine("OPEN",StringFormat("side=%s lots=%.4f price=%.5f ticket=%I64u",side,InpLots,trade.ResultPrice(),g_position_ticket));
   return (g_position_ticket!=0);
}

void TryTimedExit()
{
   if(!InpEnableTrading) return;
   if(!RefreshOurPosition()) return;

   datetime bar0=iTime(InpSymbol,PERIOD_M5,0);
   if(bar0<=0 || g_entry_bar_time<=0) return;
   int bars_elapsed=(int)((bar0-g_entry_bar_time)/300);
   if(bars_elapsed<InpExitBars) return;

   ulong ticket=g_position_ticket;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(trade.PositionClose(ticket,(ulong)InpMaxDeviationPoints))
   {
      LogLine("CLOSE",StringFormat("bars_elapsed=%d price=%.5f ticket=%I64u",bars_elapsed,trade.ResultPrice(),ticket));
      g_position_ticket=0;
      g_entry_bar_time=0;
   }
   else
   {
      Print("R18 close failed ticket=",ticket," retcode=",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      LogLine("CLOSE_FAIL",StringFormat("ticket=%I64u retcode=%u %s",ticket,trade.ResultRetcode(),trade.ResultRetcodeDescription()));
   }
}

int OnInit()
{
   if(_Symbol!=InpSymbol){ Print("Attach to exact symbol ",InpSymbol,". Current chart=",_Symbol); return INIT_FAILED; }
   if(_Period!=PERIOD_M5){ Print("Attach to M5 chart only."); return INIT_FAILED; }
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
   else Print("R18 log FileOpen failed err=",GetLastError());

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   g_last_bar0=iTime(InpSymbol,PERIOD_M5,0);
   RefreshOurPosition();

   Print("R18_XAUUSD_EA_MVP_v1_01 active. Trading=",(InpEnableTrading?"ON":"OFF (dry-run)"));
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
   g_last_bar0=bar0;

   TryTimedExit();
   if(RefreshOurPosition()) return;

   double bar_return=0.0, score=0.0;
   int shock_direction=0;
   if(!ComputeShock(bar_return,score,shock_direction)) return;
   if(score<InpShockThreshold) return;

   OpenContrarian(shock_direction,score,bar_return);
}
