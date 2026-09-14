#property strict
#property version "1.00"
#property description "Observation-only XAUUSD quote logger for R18 cost study. No order functions."

input string InpSymbol = "XAUUSD";
input string InpPrefix = "R18_XAUUSD_QUOTES_v1_00";
input bool InpLogEveryTick = true;

int g_tick_file = INVALID_HANDLE;
int g_bar_file = INVALID_HANDLE;
datetime g_last_bar0 = 0;

string TickFileName(){ return InpPrefix + "_ticks.csv"; }
string BarFileName(){ return InpPrefix + "_m5.csv"; }

bool OpenAppend(const string name,int &handle,const string header)
{
   handle=FileOpen(name,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,',');
   if(handle==INVALID_HANDLE)
   {
      Print("QuoteObserver FileOpen failed: ",name," err=",GetLastError());
      return false;
   }
   if(FileSize(handle)==0) FileWriteString(handle,header+"\r\n");
   FileSeek(handle,0,SEEK_END);
   return true;
}

double Mid(const MqlTick &t){ return (t.bid+t.ask)*0.5; }

double SpreadBps(const MqlTick &t)
{
   double m=Mid(t);
   if(m<=0.0) return 0.0;
   return (t.ask-t.bid)/m*10000.0;
}

void WriteTick(const MqlTick &t)
{
   if(!InpLogEveryTick || g_tick_file==INVALID_HANDLE) return;
   FileWrite(g_tick_file,
      (long)t.time_msc,
      TimeToString(t.time,TIME_DATE|TIME_SECONDS),
      DoubleToString(t.bid,_Digits),
      DoubleToString(t.ask,_Digits),
      DoubleToString(Mid(t),_Digits),
      DoubleToString(SpreadBps(t),8));
   FileFlush(g_tick_file);
}

void WriteClosedBar()
{
   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(InpSymbol,PERIOD_M5,1,1,r)!=1) return;
   FileWrite(g_bar_file,
      (long)r[0].time,
      TimeToString(r[0].time,TIME_DATE|TIME_MINUTES),
      DoubleToString(r[0].open,_Digits),
      DoubleToString(r[0].high,_Digits),
      DoubleToString(r[0].low,_Digits),
      DoubleToString(r[0].close,_Digits),
      (long)r[0].tick_volume);
   FileFlush(g_bar_file);
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

   if(!OpenAppend(TickFileName(),g_tick_file,"time_msc,time_server,bid,ask,mid,spread_bps")) return INIT_FAILED;
   if(!OpenAppend(BarFileName(),g_bar_file,"bar_epoch,bar_time,open,high,low,close,tick_volume")) return INIT_FAILED;

   g_last_bar0=iTime(InpSymbol,PERIOD_M5,0);
   Print("R18 XAUUSD QuoteObserver v1.00 active. Observation only; no order API is used.");
   Print("Output in MQL5/Files/: ",TickFileName()," and ",BarFileName());
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_tick_file!=INVALID_HANDLE) FileClose(g_tick_file);
   if(g_bar_file!=INVALID_HANDLE) FileClose(g_bar_file);
}

void OnTick()
{
   MqlTick t;
   if(!SymbolInfoTick(InpSymbol,t)) return;
   if(t.bid<=0.0 || t.ask<=0.0 || t.ask<t.bid) return;

   WriteTick(t);

   datetime bar0=iTime(InpSymbol,PERIOD_M5,0);
   if(bar0<=0 || bar0==g_last_bar0) return;
   WriteClosedBar();
   g_last_bar0=bar0;
}
