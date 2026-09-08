#property strict
#property script_show_inputs
#property version   "1.00"
#property description "Guardian Phase I-A: export 2024-2025 high-impact MT5 economic calendar in trade-server time."

input datetime InpFrom = D'2024.01.01 00:00:00';
input datetime InpTo   = D'2026.01.01 00:00:00';
input string   InpCurrencies = "USD,EUR,GBP,JPY,CHF,CAD,AUD,NZD";
input string   InpOutputCsv = "Guardian\\phase_ia\\mt5_high_impact_calendar_2024_2025.csv";
input string   InpManifestTxt = "Guardian\\phase_ia\\mt5_calendar_terminal_manifest.txt";

string Clean(const string s)
  {
   string x=s;
   StringReplace(x,"\r"," ");
   StringReplace(x,"\n"," ");
   return x;
  }

void WriteManifest()
  {
   int h=FileOpen(InpManifestTxt,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h==INVALID_HANDLE)
     {
      PrintFormat("I-A manifest open failed: %d",GetLastError());
      return;
     }
   FileWriteString(h,"schema=1\r\n");
   FileWriteString(h,"phase=I-A\r\n");
   FileWriteString(h,"terminal_path="+TerminalInfoString(TERMINAL_PATH)+"\r\n");
   FileWriteString(h,"terminal_data_path="+TerminalInfoString(TERMINAL_DATA_PATH)+"\r\n");
   FileWriteString(h,"terminal_commondata_path="+TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\r\n");
   FileWriteString(h,"company="+AccountInfoString(ACCOUNT_COMPANY)+"\r\n");
   FileWriteString(h,"server="+AccountInfoString(ACCOUNT_SERVER)+"\r\n");
   FileWriteString(h,"currency="+AccountInfoString(ACCOUNT_CURRENCY)+"\r\n");
   FileWriteString(h,"from_server_time="+TimeToString(InpFrom,TIME_DATE|TIME_MINUTES|TIME_SECONDS)+"\r\n");
   FileWriteString(h,"to_server_time_exclusive="+TimeToString(InpTo,TIME_DATE|TIME_MINUTES|TIME_SECONDS)+"\r\n");
   FileWriteString(h,"exported_at_server_time="+TimeToString(TimeTradeServer(),TIME_DATE|TIME_MINUTES|TIME_SECONDS)+"\r\n");
   FileWriteString(h,"currencies="+InpCurrencies+"\r\n");
   FileClose(h);
  }

void OnStart()
  {
   if(InpFrom<=0 || InpTo<=InpFrom || InpTo>D'2026.01.01 00:00:00')
     {
      Print("I-A REFUSED: invalid date range or protected 2026 would be opened.");
      return;
     }

   int h=FileOpen(InpOutputCsv,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)
     {
      PrintFormat("I-A CSV open failed: %d",GetLastError());
      return;
     }

   FileWrite(h,
             "value_id","event_id","server_time","server_epoch","event_code","event_name",
             "country_code","country_name","currency","importance","event_type","sector",
             "time_mode","frequency","source_url","revision");

   string currencies[];
   int ncur=StringSplit(InpCurrencies,',',currencies);
   long rows=0;
   long event_types=0;
   long errors=0;

   for(int ci=0;ci<ncur;ci++)
     {
      StringTrimLeft(currencies[ci]);
      StringTrimRight(currencies[ci]);
      string cur=currencies[ci];
      if(StringLen(cur)==0)
         continue;

      MqlCalendarEvent events[];
      ResetLastError();
      int ne=CalendarEventByCurrency(cur,events);
      if(ne<0)
        {
         PrintFormat("I-A CalendarEventByCurrency failed currency=%s err=%d",cur,GetLastError());
         errors++;
         continue;
        }

      PrintFormat("I-A %s: %d event definitions",cur,ne);
      for(int ei=0;ei<ne;ei++)
        {
         if(events[ei].importance!=CALENDAR_IMPORTANCE_HIGH)
            continue;
         if(events[ei].type==CALENDAR_TYPE_HOLIDAY)
            continue;

         MqlCalendarCountry country;
         ZeroMemory(country);
         if(!CalendarCountryById(events[ei].country_id,country))
           {
            PrintFormat("I-A CalendarCountryById failed event=%I64u err=%d",events[ei].id,GetLastError());
            errors++;
            continue;
           }

         MqlCalendarValue vals[];
         ResetLastError();
         int nv=CalendarValueHistoryByEvent(events[ei].id,vals,InpFrom,InpTo);
         if(nv<0)
           {
            PrintFormat("I-A CalendarValueHistoryByEvent failed event=%I64u %s err=%d",events[ei].id,events[ei].name,GetLastError());
            errors++;
            continue;
           }
         if(nv==0)
            continue;

         event_types++;
         for(int vi=0;vi<nv;vi++)
           {
            if(vals[vi].time<InpFrom || vals[vi].time>=InpTo)
               continue;
            FileWrite(h,
                      (long)vals[vi].id,
                      (long)events[ei].id,
                      TimeToString(vals[vi].time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                      (long)vals[vi].time,
                      Clean(events[ei].event_code),
                      Clean(events[ei].name),
                      Clean(country.code),
                      Clean(country.name),
                      Clean(cur),
                      (int)events[ei].importance,
                      (int)events[ei].type,
                      (int)events[ei].sector,
                      (int)events[ei].time_mode,
                      (int)events[ei].frequency,
                      Clean(events[ei].source_url),
                      vals[vi].revision);
            rows++;
           }
        }
     }

   FileClose(h);
   WriteManifest();
   PrintFormat("I-A COMPLETE rows=%I64d high_impact_event_types=%I64d errors=%I64d output=%s",rows,event_types,errors,InpOutputCsv);
  }
