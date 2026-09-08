#property strict
#property script_show_inputs
#property version   "1.01"
#property description "Guardian Phase I-B v1.01: resilient XAUUSD M1/M5 2024-2025 exporter with history-sync retries and machine-readable status."

input string   InpSymbolRoot = "XAUUSD";
input datetime InpFrom = D'2024.01.01 00:00:00';
input datetime InpToExclusive = D'2026.01.01 00:00:00';
input string   InpOutputM1 = "Guardian\\phase_ib\\xauusd_m1_2024_2025_raw.csv";
input string   InpOutputM5 = "Guardian\\phase_ib\\xauusd_m5_2024_2025_raw.csv";
input string   InpManifestTxt = "Guardian\\phase_ib\\xauusd_history_terminal_manifest.txt";
input string   InpStatusTxt = "Guardian\\phase_ib\\xauusd_history_status.txt";
input int      InpMaxHistoryWaitSeconds = 180;

void WriteStatus(const string state,const string reason,const string detail="")
  {
   int h=FileOpen(InpStatusTxt,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h==INVALID_HANDLE)
     {
      PrintFormat("I-B status open failed err=%d",GetLastError());
      return;
     }
   FileWriteString(h,"schema=1\r\n");
   FileWriteString(h,"phase=I-B\r\n");
   FileWriteString(h,"exporter_version=1.01\r\n");
   FileWriteString(h,"state="+state+"\r\n");
   FileWriteString(h,"reason="+reason+"\r\n");
   FileWriteString(h,"detail="+detail+"\r\n");
   FileWriteString(h,"server="+AccountInfoString(ACCOUNT_SERVER)+"\r\n");
   FileWriteString(h,"terminal_path="+TerminalInfoString(TERMINAL_PATH)+"\r\n");
   FileWriteString(h,"terminal_data_path="+TerminalInfoString(TERMINAL_DATA_PATH)+"\r\n");
   FileWriteString(h,"server_time="+TimeToString(TimeTradeServer(),TIME_DATE|TIME_MINUTES|TIME_SECONDS)+"\r\n");
   FileClose(h);
  }

string ResolveSymbol()
  {
   if(SymbolSelect(InpSymbolRoot,true))
      return InpSymbolRoot;

   int total=SymbolsTotal(false);
   string candidate="";
   int matches=0;
   for(int i=0;i<total;i++)
     {
      string s=SymbolName(i,false);
      if(StringFind(s,InpSymbolRoot)==0)
        {
         candidate=s;
         matches++;
        }
     }
   if(matches==1 && SymbolSelect(candidate,true))
      return candidate;

   WriteStatus("FAIL","SYMBOL_RESOLUTION_FAILED",StringFormat("root=%s matches=%d",InpSymbolRoot,matches));
   PrintFormat("I-B REFUSED: symbol root %s resolved to %d candidates.",InpSymbolRoot,matches);
   return "";
  }

datetime NextMonth(datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t,d);
   d.day=1;
   d.hour=0;
   d.min=0;
   d.sec=0;
   d.mon++;
   if(d.mon>12)
     {
      d.mon=1;
      d.year++;
     }
   return StructToTime(d);
  }

int CopyRatesWithRetry(const string symbol,
                       const ENUM_TIMEFRAMES tf,
                       const string tf_name,
                       const datetime from_time,
                       const datetime to_time,
                       MqlRates &rates[])
  {
   int waited=0;
   while(waited<=InpMaxHistoryWaitSeconds)
     {
      ArrayFree(rates);
      ArraySetAsSeries(rates,false);
      ResetLastError();
      int copied=CopyRates(symbol,tf,from_time,to_time,rates);
      int err=GetLastError();
      if(copied>0)
         return copied;

      // CopyRates can legitimately return -1/0 while the terminal is downloading/building history.
      // Bars() is called as an additional synchronization trigger; the script then waits and retries.
      ResetLastError();
      int bars=Bars(symbol,tf,from_time,to_time);
      int bars_err=GetLastError();
      if(waited==0 || waited%10==0)
        {
         PrintFormat("I-B WAIT history tf=%s from=%s to=%s copied=%d err=%d bars=%d bars_err=%d waited=%ds",
                     tf_name,
                     TimeToString(from_time,TIME_DATE|TIME_MINUTES),
                     TimeToString(to_time,TIME_DATE|TIME_MINUTES),
                     copied,err,bars,bars_err,waited);
        }
      Sleep(1000);
      waited++;
     }
   return -1;
  }

bool ExportTimeframe(const string symbol,
                     const ENUM_TIMEFRAMES tf,
                     const string tf_name,
                     const string filename,
                     long &rows_written,
                     long &first_epoch,
                     long &last_epoch,
                     string &failure_detail)
  {
   int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   int h=FileOpen(filename,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)
     {
      failure_detail=StringFormat("FileOpen failed tf=%s file=%s err=%d",tf_name,filename,GetLastError());
      return false;
     }

   FileWrite(h,"symbol","timeframe","server_time","server_epoch","open","high","low","close","tick_volume","spread","real_volume");
   rows_written=0;
   first_epoch=0;
   last_epoch=0;

   datetime cursor=InpFrom;
   while(cursor<InpToExclusive)
     {
      datetime next=NextMonth(cursor);
      if(next>InpToExclusive)
         next=InpToExclusive;
      datetime end_inclusive=next-1;

      MqlRates rates[];
      int copied=CopyRatesWithRetry(symbol,tf,tf_name,cursor,end_inclusive,rates);
      if(copied<=0)
        {
         FileClose(h);
         failure_detail=StringFormat("History timeout tf=%s from=%s to=%s wait=%ds",
                                     tf_name,
                                     TimeToString(cursor,TIME_DATE|TIME_MINUTES),
                                     TimeToString(end_inclusive,TIME_DATE|TIME_MINUTES),
                                     InpMaxHistoryWaitSeconds);
         return false;
        }

      PrintFormat("I-B %s %s -> %s copied=%d",
                  tf_name,
                  TimeToString(cursor,TIME_DATE|TIME_MINUTES),
                  TimeToString(end_inclusive,TIME_DATE|TIME_MINUTES),
                  copied);

      for(int i=0;i<copied;i++)
        {
         long epoch=(long)rates[i].time;
         if(rates[i].time<InpFrom || rates[i].time>=InpToExclusive)
            continue;
         if(first_epoch==0)
            first_epoch=epoch;
         last_epoch=epoch;
         FileWrite(h,
                   symbol,
                   tf_name,
                   TimeToString(rates[i].time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                   epoch,
                   DoubleToString(rates[i].open,digits),
                   DoubleToString(rates[i].high,digits),
                   DoubleToString(rates[i].low,digits),
                   DoubleToString(rates[i].close,digits),
                   (long)rates[i].tick_volume,
                   rates[i].spread,
                   (long)rates[i].real_volume);
         rows_written++;
        }
      FileFlush(h);
      cursor=next;
     }

   FileClose(h);
   if(rows_written<=0)
     {
      failure_detail="No rows written for "+tf_name;
      return false;
     }
   return true;
  }

bool WriteManifest(const string symbol,
                   const long m1_rows,
                   const long m1_first,
                   const long m1_last,
                   const long m5_rows,
                   const long m5_first,
                   const long m5_last)
  {
   int h=FileOpen(InpManifestTxt,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h==INVALID_HANDLE)
     {
      PrintFormat("I-B manifest open failed err=%d",GetLastError());
      return false;
     }
   FileWriteString(h,"schema=1\r\n");
   FileWriteString(h,"phase=I-B\r\n");
   FileWriteString(h,"exporter_version=1.01\r\n");
   FileWriteString(h,"symbol="+symbol+"\r\n");
   FileWriteString(h,"symbol_root="+InpSymbolRoot+"\r\n");
   FileWriteString(h,"server="+AccountInfoString(ACCOUNT_SERVER)+"\r\n");
   FileWriteString(h,"company="+AccountInfoString(ACCOUNT_COMPANY)+"\r\n");
   FileWriteString(h,"terminal_path="+TerminalInfoString(TERMINAL_PATH)+"\r\n");
   FileWriteString(h,"terminal_data_path="+TerminalInfoString(TERMINAL_DATA_PATH)+"\r\n");
   FileWriteString(h,"terminal_commondata_path="+TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\r\n");
   FileWriteString(h,"from_server_time="+TimeToString(InpFrom,TIME_DATE|TIME_MINUTES|TIME_SECONDS)+"\r\n");
   FileWriteString(h,"to_server_time_exclusive="+TimeToString(InpToExclusive,TIME_DATE|TIME_MINUTES|TIME_SECONDS)+"\r\n");
   FileWriteString(h,"exported_at_server_time="+TimeToString(TimeTradeServer(),TIME_DATE|TIME_MINUTES|TIME_SECONDS)+"\r\n");
   FileWriteString(h,"m1_rows="+(string)m1_rows+"\r\n");
   FileWriteString(h,"m1_first_epoch="+(string)m1_first+"\r\n");
   FileWriteString(h,"m1_last_epoch="+(string)m1_last+"\r\n");
   FileWriteString(h,"m5_rows="+(string)m5_rows+"\r\n");
   FileWriteString(h,"m5_first_epoch="+(string)m5_first+"\r\n");
   FileWriteString(h,"m5_last_epoch="+(string)m5_last+"\r\n");
   FileClose(h);
   return true;
  }

void OnStart()
  {
   WriteStatus("RUNNING","STARTED");

   if(InpFrom<=0 || InpToExclusive<=InpFrom || InpToExclusive>D'2026.01.01 00:00:00')
     {
      WriteStatus("FAIL","DATE_GUARD_FAILED","Invalid date range or protected 2026 would be opened");
      return;
     }

   string symbol=ResolveSymbol();
   if(symbol=="")
      return;

   long m1_rows=0,m1_first=0,m1_last=0;
   long m5_rows=0,m5_first=0,m5_last=0;
   string detail="";

   PrintFormat("I-B START v1.01 symbol=%s server=%s data_path=%s",symbol,AccountInfoString(ACCOUNT_SERVER),TerminalInfoString(TERMINAL_DATA_PATH));

   if(!ExportTimeframe(symbol,PERIOD_M1,"M1",InpOutputM1,m1_rows,m1_first,m1_last,detail))
     {
      WriteStatus("FAIL","M1_EXPORT_FAILED",detail);
      return;
     }
   if(!ExportTimeframe(symbol,PERIOD_M5,"M5",InpOutputM5,m5_rows,m5_first,m5_last,detail))
     {
      WriteStatus("FAIL","M5_EXPORT_FAILED",detail);
      return;
     }

   if(!WriteManifest(symbol,m1_rows,m1_first,m1_last,m5_rows,m5_first,m5_last))
     {
      WriteStatus("FAIL","MANIFEST_WRITE_FAILED");
      return;
     }

   WriteStatus("SUCCESS","COMPLETE",StringFormat("symbol=%s M1=%I64d M5=%I64d",symbol,m1_rows,m5_rows));
   PrintFormat("I-B COMPLETE v1.01 symbol=%s M1=%I64d M5=%I64d",symbol,m1_rows,m5_rows);
  }
