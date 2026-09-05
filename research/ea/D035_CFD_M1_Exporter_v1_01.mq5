#property strict
#property version   "1.01"
#property description "D035 FundedNext crypto CFD M1 quote exporter for cross-venue lead-lag research. No orders."

#define EXPERIMENT_ID "D035_CFD_M1_EXPORT"

int g_file=INVALID_HANDLE;
string g_run_dir="";
datetime g_bucket=0;
bool g_have=false;
double g_bid_first=0.0,g_ask_first=0.0,g_bid_last=0.0,g_ask_last=0.0;
long g_tick_count=0;
long g_minutes_written=0;

string RunTag(){
   MqlDateTime d; TimeToStruct(TimeLocal(),d);
   return StringFormat("RUN_%04d%02d%02d_%02d%02d%02d_%u",d.year,d.mon,d.day,d.hour,d.min,d.sec,(uint)GetTickCount());
}

double Mid(const double bid,const double ask){ if(bid<=0.0 || ask<=0.0) return 0.0; return 0.5*(bid+ask); }
double SpreadBps(const double bid,const double ask){ double m=Mid(bid,ask); if(m<=0.0) return 0.0; return (ask-bid)/m*10000.0; }

bool EnsureFolders(){
   string a="GuardianResearch";
   string b=a+"\\SETUP_SCANS";
   string c=b+"\\"+EXPERIMENT_ID;
   string d=c+"\\"+_Symbol;
   string e=d+"\\"+RunTag();
   FolderCreate(a,FILE_COMMON); FolderCreate(b,FILE_COMMON); FolderCreate(c,FILE_COMMON); FolderCreate(d,FILE_COMMON); FolderCreate(e,FILE_COMMON);
   g_run_dir=e; return true;
}

void ResetMinute(const datetime bucket,const MqlTick &tick){
   g_bucket=bucket; g_bid_first=tick.bid; g_ask_first=tick.ask; g_bid_last=tick.bid; g_ask_last=tick.ask; g_tick_count=1; g_have=true;
}

void WriteMinute(){
   if(!g_have || g_file==INVALID_HANDLE) return;
   MqlDateTime d; TimeToStruct(g_bucket,d);
   FileWrite(g_file,
      EXPERIMENT_ID,_Symbol,TimeToString(g_bucket,TIME_DATE|TIME_MINUTES),(long)g_bucket,
      g_bid_first,g_ask_first,g_bid_last,g_ask_last,Mid(g_bid_first,g_ask_first),Mid(g_bid_last,g_ask_last),
      SpreadBps(g_bid_first,g_ask_first),SpreadBps(g_bid_last,g_ask_last),g_tick_count,
      d.year,d.mon,d.day,d.hour,d.min,d.day_of_week);
   g_minutes_written++;
   if((g_minutes_written%250)==0) FileFlush(g_file);
}

int OnInit(){
   EnsureFolders();
   g_file=FileOpen(g_run_dir+"\\D035_CFD_M1_"+_Symbol+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,';');
   if(g_file==INVALID_HANDLE){ Print("D035 exporter failed opening file. Error=",GetLastError()); return INIT_FAILED; }
   FileWrite(g_file,
      "experiment","symbol","server_minute","server_epoch_s","bid_first","ask_first","bid_last","ask_last","mid_first","mid_last",
      "spread_first_bps","spread_last_bps","tick_count","server_year","server_month","server_day","server_hour","server_minute_num","server_dow");
   FileFlush(g_file);
   if(FileSize(g_file)<=0){ Print("D035 exporter header QA failed."); return INIT_FAILED; }
   Print("D035 exporter ready: ",g_run_dir); return INIT_SUCCEEDED;
}

void OnTick(){
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return; if(tick.bid<=0.0 || tick.ask<=0.0) return;
   datetime bucket=(datetime)(((long)tick.time/60)*60);
   if(!g_have){ ResetMinute(bucket,tick); return; }
   if(bucket==g_bucket){ g_bid_last=tick.bid; g_ask_last=tick.ask; g_tick_count++; return; }
   WriteMinute(); ResetMinute(bucket,tick);
}

void OnDeinit(const int reason){
   WriteMinute();
   if(g_file!=INVALID_HANDLE){ FileFlush(g_file); FileClose(g_file); }
}
