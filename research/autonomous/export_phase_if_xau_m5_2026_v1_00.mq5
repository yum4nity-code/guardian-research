#property script_show_inputs
#property strict

input string InpSymbol = "XAUUSD";

void OnStart()
{
   datetime from = D'2026.01.01 00:00:00';
   datetime to   = D'2026.09.01 00:00:00';
   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   ResetLastError();
   int n=CopyRates(InpSymbol,PERIOD_M5,from,to,rates);
   if(n<=0){ PrintFormat("I-F XAU M5 EXPORT FAIL CopyRates=%d err=%d",n,GetLastError()); return; }
   string rel="Guardian\\phase_if\\xauusd_m5_2026_jan_aug.csv";
   int h=FileOpen(rel,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE){ PrintFormat("I-F XAU M5 EXPORT FAIL FileOpen err=%d",GetLastError()); return; }
   FileWrite(h,"server_time","server_epoch","open","high","low","close","tick_volume","spread","real_volume");
   int written=0;
   for(int i=0;i<n;i++){
      if(rates[i].time<from || rates[i].time>=to) continue;
      FileWrite(h,TimeToString(rates[i].time,TIME_DATE|TIME_SECONDS),(long)rates[i].time,
                DoubleToString(rates[i].open,8),DoubleToString(rates[i].high,8),DoubleToString(rates[i].low,8),DoubleToString(rates[i].close,8),
                (long)rates[i].tick_volume,(int)rates[i].spread,(long)rates[i].real_volume);
      written++;
   }
   FileClose(h);
   string man="Guardian\\phase_if\\xauusd_m5_2026_jan_aug_manifest.txt";
   int m=FileOpen(man,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(m!=INVALID_HANDLE){
      FileWriteString(m,"symbol="+InpSymbol+"\r\n");
      FileWriteString(m,"period=M5\r\nfrom=2026.01.01 00:00:00\r\nto_exclusive=2026.09.01 00:00:00\r\n");
      FileWriteString(m,"terminal_path="+TerminalInfoString(TERMINAL_PATH)+"\r\n");
      FileWriteString(m,"terminal_data_path="+TerminalInfoString(TERMINAL_DATA_PATH)+"\r\n");
      FileWriteString(m,"company="+TerminalInfoString(TERMINAL_COMPANY)+"\r\n");
      FileWriteString(m,"server="+AccountInfoString(ACCOUNT_SERVER)+"\r\n");
      FileWriteString(m,"rows="+IntegerToString(written)+"\r\n");
      FileClose(m);
   }
   PrintFormat("I-F XAU M5 EXPORT COMPLETE rows=%d output=%s",written,rel);
}
