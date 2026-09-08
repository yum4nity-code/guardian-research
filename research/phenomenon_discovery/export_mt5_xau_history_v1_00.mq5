#property strict
#property script_show_inputs
#property version   "1.00"
#property description "Guardian Phase I-B: export XAUUSD M1/M5 2024-2025 from the currently running MT5 server."

input string   InpSymbolRoot = "XAUUSD";
input datetime InpFrom = D'2024.01.01 00:00:00';
input datetime InpToExclusive = D'2026.01.01 00:00:00';
input string   InpOutputM1 = "Guardian\\phase_ib\\xauusd_m1_2024_2025_raw.csv";
input string   InpOutputM5 = "Guardian\\phase_ib\\xauusd_m5_2024_2025_raw.csv";
input string   InpManifestTxt = "Guardian\\phase_ib\\xauusd_history_terminal_manifest.txt";

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

bool ExportTimeframe(const string symbol,
                     const ENUM_TIMEFRAMES tf,
                     const string tf_name,
                     const string filename,
                     long &rows_written,
                     long &first_epoch,
                     long &last_epoch)
  {
   int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   int h=FileOpen(filename,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)
     {
      PrintFormat("I-B FileOpen failed %s err=%d",filename,GetLastError());
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
      ArraySetAsSeries(rates,false);
      ResetLastError();
      int copied=CopyRates(symbol,tf,cursor,end_inclusive,rates);
      if(copied<0)
        {
         int err=GetLastError();
         FileClose(h);
         PrintFormat("I-B CopyRates failed tf=%s from=%s to=%s err=%d",
                     tf_name,
                     TimeToString(cursor,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                     TimeToString(end_inclusive,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                     err);
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

      cursor=next;
     }

   FileClose(h);
   return true;
  }

void WriteManifest(const string symbol,
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
      return;
     }
   FileWriteString(h,"schema=1\r\n");
   FileWriteString(h,"phase=I-B\r\n");
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
  }

void OnStart()
  {
   if(InpFrom<=0 || InpToExclusive<=InpFrom || InpToExclusive>D'2026.01.01 00:00:00')
     {
      Print("I-B REFUSED: invalid date range or protected 2026 would be opened.");
      return;
     }

   string symbol=ResolveSymbol();
   if(symbol=="")
      return;

   long m1_rows=0,m1_first=0,m1_last=0;
   long m5_rows=0,m5_first=0,m5_last=0;

   PrintFormat("I-B START symbol=%s server=%s data_path=%s",symbol,AccountInfoString(ACCOUNT_SERVER),TerminalInfoString(TERMINAL_DATA_PATH));

   if(!ExportTimeframe(symbol,PERIOD_M1,"M1",InpOutputM1,m1_rows,m1_first,m1_last))
      return;
   if(!ExportTimeframe(symbol,PERIOD_M5,"M5",InpOutputM5,m5_rows,m5_first,m5_last))
      return;

   WriteManifest(symbol,m1_rows,m1_first,m1_last,m5_rows,m5_first,m5_last);
   PrintFormat("I-B COMPLETE symbol=%s M1=%I64d M5=%I64d",symbol,m1_rows,m5_rows);
  }
