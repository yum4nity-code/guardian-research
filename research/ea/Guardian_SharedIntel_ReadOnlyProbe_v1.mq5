#property strict
#property version   "1.02"
#property description "Guardian Shared Intelligence read-only FILE_COMMON probe"

input string InpSharedFile = "GuardianSharedIntelligence\\market_state_v1.csv";
input int    InpPollMilliseconds = 250;
input int    InpJournalEverySeconds = 30;

#define FIELD_COUNT 33

long     g_last_generation = -1;
string   g_terminal_id = "";
string   g_probe_file = "";
string   g_server = "";
string   g_data_path = "";
datetime g_last_journal_time = 0;
datetime g_last_issue_time = 0;
string   g_last_btc_status = "";
string   g_last_eth_status = "";

uint HashString32(const string value)
{
   uint h = 2166136261;
   const int n = StringLen(value);
   for(int i=0; i<n; i++)
   {
      h ^= (uint)StringGetCharacter(value, i);
      h *= 16777619;
   }
   return h;
}

bool ShouldPrintIssue()
{
   const datetime now = TimeLocal();
   if(g_last_issue_time == 0 || (now - g_last_issue_time) >= 10)
   {
      g_last_issue_time = now;
      return true;
   }
   return false;
}

bool ReadCsvRow(const int handle, string &row[])
{
   ArrayResize(row, FIELD_COUNT);
   for(int i=0; i<FIELD_COUNT; i++)
   {
      if(FileIsEnding(handle) && i==0)
         return false;
      row[i] = FileReadString(handle);
   }
   return true;
}

bool ReadSharedState(long &generation,
                     string &btc_status,
                     string &eth_status,
                     double &btc_spot,
                     double &eth_spot)
{
   ResetLastError();
   const int handle = FileOpen(InpSharedFile,
                               FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,
                               ';');
   if(handle == INVALID_HANDLE)
   {
      if(ShouldPrintIssue())
         PrintFormat("[SHAREDINTEL][READ][WAIT] file=%s err=%d", InpSharedFile, GetLastError());
      return false;
   }

   string header[], row1[], row2[];
   bool ok = ReadCsvRow(handle, header) && ReadCsvRow(handle, row1) && ReadCsvRow(handle, row2);
   FileClose(handle);
   if(!ok)
   {
      if(ShouldPrintIssue())
         Print("[SHAREDINTEL][READ][REVIEW] CSV incomplete");
      return false;
   }

   const long gen1 = (long)StringToInteger(row1[1]);
   const long gen2 = (long)StringToInteger(row2[1]);
   if(gen1 <= 0 || gen1 != gen2)
   {
      if(ShouldPrintIssue())
         PrintFormat("[SHAREDINTEL][READ][REVIEW] incoherent generations %I64d / %I64d", gen1, gen2);
      return false;
   }

   string btc[], eth[];
   if(row1[3] == "BTCUSD" && row2[3] == "ETHUSD")
   {
      ArrayCopy(btc, row1);
      ArrayCopy(eth, row2);
   }
   else if(row1[3] == "ETHUSD" && row2[3] == "BTCUSD")
   {
      ArrayCopy(btc, row2);
      ArrayCopy(eth, row1);
   }
   else
   {
      if(ShouldPrintIssue())
         PrintFormat("[SHAREDINTEL][READ][REVIEW] unexpected symbols %s / %s", row1[3], row2[3]);
      return false;
   }

   generation = gen1;
   btc_status = btc[4];
   eth_status = eth[4];
   btc_spot = StringToDouble(btc[6]);
   eth_spot = StringToDouble(eth[6]);
   return true;
}

void AppendProbeObservation(const long generation,
                            const string btc_status,
                            const string eth_status)
{
   ResetLastError();
   const int h = FileOpen(g_probe_file,
                          FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE,
                          ';');
   if(h == INVALID_HANDLE)
   {
      if(ShouldPrintIssue())
         PrintFormat("[SHAREDINTEL][PROBE][REVIEW] cannot open probe file err=%d", GetLastError());
      return;
   }

   if(FileSize(h) == 0)
      FileWrite(h, "terminal_id", "observed_local_time", "generation_id", "btc_status", "eth_status", "server", "data_path");

   FileSeek(h, 0, SEEK_END);
   FileWrite(h,
             g_terminal_id,
             TimeToString(TimeLocal(), TIME_DATE|TIME_SECONDS),
             IntegerToString(generation),
             btc_status,
             eth_status,
             g_server,
             g_data_path);
   FileFlush(h);
   FileClose(h);
}

int OnInit()
{
   g_data_path = TerminalInfoString(TERMINAL_DATA_PATH);
   g_server = AccountInfoString(ACCOUNT_SERVER);
   const uint id_hash = HashString32(g_data_path + "|" + g_server);
   g_terminal_id = StringFormat("T%08X", id_hash);
   // v102 suffix deliberately starts a fresh schema so old 5-column probe files
   // cannot be mistaken for this identity-aware validation run.
   g_probe_file = StringFormat("GuardianSharedIntelligence\\probes\\probe_%s_v102.csv", g_terminal_id);

   PrintFormat("[SHAREDINTEL][PROBE][START] terminal_id=%s server=%s data=%s common=%s",
               g_terminal_id,
               g_server,
               g_data_path,
               TerminalInfoString(TERMINAL_COMMONDATA_PATH));
   Print("[SHAREDINTEL][PROBE] READ ONLY: no CTrade, no OrderSend, no position modification.");

   EventSetMillisecondTimer((int)MathMax(100, InpPollMilliseconds));
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   PrintFormat("[SHAREDINTEL][PROBE][STOP] terminal_id=%s reason=%d", g_terminal_id, reason);
}

void OnTimer()
{
   long generation;
   string btc_status, eth_status;
   double btc_spot, eth_spot;
   if(!ReadSharedState(generation, btc_status, eth_status, btc_spot, eth_spot))
      return;

   if(generation == g_last_generation)
      return;

   g_last_generation = generation;
   AppendProbeObservation(generation, btc_status, eth_status);

   const datetime now = TimeLocal();
   const bool status_changed = (btc_status != g_last_btc_status || eth_status != g_last_eth_status);
   const bool periodic = (InpJournalEverySeconds > 0 &&
                          (g_last_journal_time == 0 || (now - g_last_journal_time) >= InpJournalEverySeconds));

   if(status_changed || periodic)
   {
      PrintFormat("[SHAREDINTEL][PROBE][OK] terminal_id=%s gen=%I64d server=%s BTC=%s spot=%.2f ETH=%s spot=%.2f",
                  g_terminal_id,
                  generation,
                  g_server,
                  btc_status,
                  btc_spot,
                  eth_status,
                  eth_spot);
      g_last_journal_time = now;
   }

   g_last_btc_status = btc_status;
   g_last_eth_status = eth_status;
}
