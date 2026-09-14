#property strict
#property version "1.01"
#property description "Observation-only XAUUSD quote logger for R18 cost study."

input string InpSymbol = "XAUUSD";
input string InpPrefix = "R18_XAUUSD_QUOTES_v1_01";
input bool InpLogEveryTick = true;
input int InpStatusSeconds = 10;

int g_tick_file = INVALID_HANDLE;
int g_bar_file = INVALID_HANDLE;
int g_status_file = INVALID_HANDLE;
datetime g_last_bar0 = 0;
long g_tick_rows = 0;
long g_bar_rows = 0;

string TickFileName(){ return InpPrefix + "_ticks.csv"; }
string BarFileName(){ return InpPrefix + "_m5.csv"; }
string StatusFileName(){ return InpPrefix + "_status.csv"; }

bool OpenAppendText(const string name,int &handle,const string header)
{
   ResetLastError();
   handle=FileOpen(name,FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(handle==INVALID_HANDLE)
   {
      Print("QuoteObserver FileOpen FAILED: ",name," err=",GetLastError());
      return false;
   }

   if(FileSize(handle)==0)
   {
      ResetLastError();
      uint n=FileWriteString(handle,header+"\r\n");
      FileFlush(handle);
      if(n==0)
      {
         Print("QuoteObserver header write FAILED: ",name," err=",GetLastError());
         FileClose(handle);
         handle=INVALID_HANDLE;
         return false;
      }
   }

   FileSeek(handle,0,SEEK_END);
   FileFlush(handle);
   return true;
}

string F(const double x){ return DoubleToString(x,_Digits); }
string F8(const double x){ return DoubleToString(x,8); }
string L(const long x){ return StringFormat("%I64d",x); }
string U(const ulong x){ return StringFormat("%I64u",x); }

double Mid(const MqlTick &t){ return (t.bid+t.ask)*0.5; }

double SpreadBps(const MqlTick &t)
{
   double m=Mid(t);
   if(m<=0.0) return 0.0;
   return (t.ask-t.bid)/m*10000.0;
}

bool AppendLine(const int handle,const string name,const string line)
{
   if(handle==INVALID_HANDLE) return false;
   ResetLastError();
   uint n=FileWriteString(handle,line+"\r\n");
   FileFlush(handle);
   if(n==0)
   {
      Print("QuoteObserver write FAILED: ",name," err=",GetLastError());
      return false;
   }
   return true;
}

bool WriteTick(const MqlTick &t)
{
   if(!InpLogEveryTick) return true;
   string line=L((long)t.time_msc)+","+
               TimeToString(t.time,TIME_DATE|TIME_SECONDS)+","+
               F(t.bid)+","+F(t.ask)+","+F(Mid(t))+","+F8(SpreadBps(t));
   if(!AppendLine(g_tick_file,TickFileName(),line)) return false;
   g_tick_rows++;
   return true;
}

bool WriteClosedBar()
{
   MqlRates r[];
   ArraySetAsSeries(r,true);
   ResetLastError();
   if(CopyRates(InpSymbol,PERIOD_M5,1,1,r)!=1)
   {
      Print("QuoteObserver CopyRates FAILED err=",GetLastError());
      return false;
   }

   string line=L((long)r[0].time)+","+
               TimeToString(r[0].time,TIME_DATE|TIME_MINUTES)+","+
               F(r[0].open)+","+F(r[0].high)+","+F(r[0].low)+","+F(r[0].close)+","+
               L((long)r[0].tick_volume);
   if(!AppendLine(g_bar_file,BarFileName(),line)) return false;
   g_bar_rows++;
   return true;
}

void WriteStatus(const string tag)
{
   if(g_status_file==INVALID_HANDLE) return;
   string line=TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS)+","+tag+","+
               L(g_tick_rows)+","+L(g_bar_rows)+","+
               U(FileSize(g_tick_file))+","+U(FileSize(g_bar_file));
   AppendLine(g_status_file,StatusFileName(),line);
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

   if(!OpenAppendText(TickFileName(),g_tick_file,"time_msc,time_server,bid,ask,mid,spread_bps")) return INIT_FAILED;
   if(!OpenAppendText(BarFileName(),g_bar_file,"bar_epoch,bar_time,open,high,low,close,tick_volume")) return INIT_FAILED;
   if(!OpenAppendText(StatusFileName(),g_status_file,"time_server,status,tick_rows,bar_rows,tick_file_bytes,bar_file_bytes")) return INIT_FAILED;

   g_last_bar0=iTime(InpSymbol,PERIOD_M5,0);

   MqlTick t;
   if(SymbolInfoTick(InpSymbol,t) && t.bid>0.0 && t.ask>=t.bid)
   {
      if(!WriteTick(t)) return INIT_FAILED;
   }

   WriteStatus("STARTUP");
   EventSetTimer(MathMax(1,InpStatusSeconds));

   Print("R18 XAUUSD QuoteObserver v1.01 ACTIVE.");
   Print("tick bytes=",FileSize(g_tick_file)," bar bytes=",FileSize(g_bar_file)," tick_rows=",g_tick_rows);
   Print("Output in MQL5/Files/: ",TickFileName(),", ",BarFileName(),", ",StatusFileName());
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   WriteStatus("STOP");
   if(g_tick_file!=INVALID_HANDLE) FileClose(g_tick_file);
   if(g_bar_file!=INVALID_HANDLE) FileClose(g_bar_file);
   if(g_status_file!=INVALID_HANDLE) FileClose(g_status_file);
}

void OnTimer()
{
   WriteStatus("HEARTBEAT");
   Print("R18 logger heartbeat: ticks=",g_tick_rows," bars=",g_bar_rows,
         " tick_bytes=",FileSize(g_tick_file)," bar_bytes=",FileSize(g_bar_file));
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
