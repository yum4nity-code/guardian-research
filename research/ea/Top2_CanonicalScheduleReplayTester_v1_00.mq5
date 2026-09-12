#property strict
#property version "1.00"
#property description "Canonical schedule replay for frozen R6B-347/R6B-307. Strategy Tester only."

#include <Trade/Trade.mqh>

input double InpVolume=1.00;

CTrade g_trade;
string g_candidate="";
long g_magic=0;
datetime g_entry[];
datetime g_exit[];
int g_next=0;
bool g_in_trade=false;
long g_position_id=0;
datetime g_actual_entry=0;
double g_entry_price=0.0;
int g_fh=INVALID_HANDLE;
long g_missed_entries=0;
long g_order_failures=0;
datetime g_last_m1=0;

string CleanSymbol(){ string s=_Symbol; StringReplace(s,".","_"); StringReplace(s,"#","_"); StringReplace(s," ","_"); return s; }

bool ResolveCandidate()
{
   string n=MQLInfoString(MQL_PROGRAM_NAME);
   if(StringFind(n,"R6B-347")==0){ g_candidate="R6B-347"; g_magic=6347101; return true; }
   if(StringFind(n,"R6B-307")==0){ g_candidate="R6B-307"; g_magic=6307101; return true; }
   return false;
}

bool LoadSchedule()
{
   string name=StringFormat("Guardian\\top2_replay\\%s_SCHEDULE.csv",g_candidate);
   int h=FileOpen(name,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,';');
   if(h==INVALID_HANDLE){ PrintFormat("%s schedule open failed err=%d",g_candidate,GetLastError()); return false; }
   if(!FileIsEnding(h)){ FileReadString(h); FileReadString(h); FileReadString(h); }
   while(!FileIsEnding(h))
   {
      string cid=FileReadString(h);
      if(cid=="" && FileIsEnding(h)) break;
      string es=FileReadString(h); string xs=FileReadString(h);
      if(cid!=g_candidate || es=="" || xs==""){ FileClose(h); return false; }
      datetime e=StringToTime(es), x=StringToTime(xs);
      if(e<=0 || x<=e || e>=D'2026.01.01 00:00:00' || x>=D'2026.01.01 00:00:00') { FileClose(h); return false; }
      int n=ArraySize(g_entry); ArrayResize(g_entry,n+1); ArrayResize(g_exit,n+1); g_entry[n]=e; g_exit[n]=x;
   }
   FileClose(h);
   return ArraySize(g_entry)>0;
}

double NetForPosition(const long pos_id,double &exit_price)
{
   double net=0.0; exit_price=0.0;
   if(!HistorySelect(g_actual_entry-3600,TimeCurrent()+3600)) return 0.0;
   int n=HistoryDealsTotal();
   for(int i=0;i<n;i++)
   {
      ulong ticket=HistoryDealGetTicket(i); if(ticket==0) continue;
      if((long)HistoryDealGetInteger(ticket,DEAL_MAGIC)!=g_magic) continue;
      if((long)HistoryDealGetInteger(ticket,DEAL_POSITION_ID)!=pos_id) continue;
      net+=HistoryDealGetDouble(ticket,DEAL_PROFIT)+HistoryDealGetDouble(ticket,DEAL_COMMISSION)+HistoryDealGetDouble(ticket,DEAL_SWAP)+HistoryDealGetDouble(ticket,DEAL_FEE);
      long en=(long)HistoryDealGetInteger(ticket,DEAL_ENTRY);
      if(en==DEAL_ENTRY_OUT || en==DEAL_ENTRY_OUT_BY) exit_price=HistoryDealGetDouble(ticket,DEAL_PRICE);
   }
   return net;
}

void LogTrade(datetime exit_time,double exit_price,double net)
{
   if(g_fh==INVALID_HANDLE) return;
   FileWrite(g_fh,g_candidate,TimeToString(g_actual_entry,TIME_DATE|TIME_MINUTES|TIME_SECONDS),TimeToString(exit_time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),DoubleToString(g_entry_price,_Digits),DoubleToString(exit_price,_Digits),DoubleToString(net,8),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2));
   FileFlush(g_fh);
}

bool OpenScheduled(datetime now)
{
   g_trade.SetExpertMagicNumber(g_magic); g_trade.SetTypeFillingBySymbol(_Symbol);
   if(!g_trade.Buy(InpVolume,_Symbol,0.0,0.0,0.0,g_candidate)){ g_order_failures++; return false; }
   if(!PositionSelect(_Symbol)){ g_order_failures++; return false; }
   g_actual_entry=now; g_entry_price=PositionGetDouble(POSITION_PRICE_OPEN); g_position_id=(long)PositionGetInteger(POSITION_IDENTIFIER); g_in_trade=true; return true;
}

bool CloseScheduled(datetime now)
{
   if(!g_in_trade) return true;
   if(!PositionSelect(_Symbol)){ g_in_trade=false; return true; }
   if((long)PositionGetInteger(POSITION_MAGIC)!=g_magic) return false;
   if(!g_trade.PositionClose(_Symbol)){ g_order_failures++; return false; }
   double xp=0.0; double net=NetForPosition(g_position_id,xp); LogTrade(now,xp,net); g_in_trade=false; g_position_id=0; return true;
}

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   if(_Period!=PERIOD_M1 || StringFind(_Symbol,"XAUUSD")<0) return INIT_PARAMETERS_INCORRECT;
   if(!ResolveCandidate() || !LoadSchedule()) return INIT_FAILED;
   g_trade.SetExpertMagicNumber(g_magic);
   string out=StringFormat("Guardian\\top2_replay\\%s_%s_TRADES.csv",g_candidate,CleanSymbol());
   g_fh=FileOpen(out,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_fh==INVALID_HANDLE) return INIT_FAILED;
   FileWrite(g_fh,"candidate_id","entry_time","exit_time","entry_price","exit_price","net_account_currency","balance_after"); FileFlush(g_fh);
   g_last_m1=iTime(_Symbol,PERIOD_M1,0);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime m1=iTime(_Symbol,PERIOD_M1,0); if(m1<=0 || m1==g_last_m1) return; g_last_m1=m1;
   if(g_in_trade)
   {
      datetime due=g_exit[g_next];
      if(m1>=due)
      {
         if(CloseScheduled(m1)) g_next++;
      }
      return;
   }
   int n=ArraySize(g_entry);
   while(g_next<n && m1>g_entry[g_next]){ g_missed_entries++; g_next++; }
   if(g_next<n && m1==g_entry[g_next]) OpenScheduled(m1);
}

void OnDeinit(const int reason)
{
   if(g_fh!=INVALID_HANDLE){ FileFlush(g_fh); FileClose(g_fh); g_fh=INVALID_HANDLE; }
   PrintFormat("%s FINAL schedule=%d consumed=%d missed=%I64d failures=%I64d",g_candidate,ArraySize(g_entry),g_next,g_missed_entries,g_order_failures);
}
