#property strict
#property version "1.00"
#property description "R6B-307 frozen long-history MT5 Strategy Tester harness. TESTER ONLY."

#include <Trade/Trade.mqh>

input double InpVolume = 1.00;

const string CANDIDATE_ID = "R6B-307";
const int LOOKBACK_BARS = 96;
const double BUFFER_ATR = 0.00;
const int HORIZON_BARS = 48;
const int SESSION_START = 0;
const int SESSION_END = 8;
const long MAGIC = 6307001;
const datetime ACTIVE_START = D'2017.01.01 00:00:00';
const datetime ACTIVE_END = D'2026.08.01 00:00:00';

CTrade g_trade;
datetime g_last_m1=0;
datetime g_last_m5=0;
double g_atr=0.0;
bool g_atr_init=false;
int g_tr_count=0;
double g_prev_close=0.0;
bool g_have_prev_close=false;
double g_highs[];
double g_lows[];
bool g_in_trade=false;
datetime g_signal_time=0;
datetime g_entry_time=0;
datetime g_exit_due=0;
double g_entry_price=0.0;
long g_position_id=0;
long g_signals=0;
long g_entries=0;
long g_exits=0;
long g_order_failures=0;
int g_fh=INVALID_HANDLE;

string CleanSymbol()
{
   string s=_Symbol;
   StringReplace(s,".","_");
   StringReplace(s,"#","_");
   StringReplace(s," ","_");
   return s;
}

void AppendHistory(const double hi,const double lo)
{
   int n=ArraySize(g_highs);
   if(n<LOOKBACK_BARS)
   {
      ArrayResize(g_highs,n+1);
      ArrayResize(g_lows,n+1);
      g_highs[n]=hi;
      g_lows[n]=lo;
      return;
   }
   for(int i=1;i<n;i++)
   {
      g_highs[i-1]=g_highs[i];
      g_lows[i-1]=g_lows[i];
   }
   g_highs[n-1]=hi;
   g_lows[n-1]=lo;
}

bool PriorRange(double &hi,double &lo)
{
   int n=ArraySize(g_highs);
   if(n<LOOKBACK_BARS) return false;
   hi=-DBL_MAX;
   lo=DBL_MAX;
   for(int i=0;i<n;i++)
   {
      if(g_highs[i]>hi) hi=g_highs[i];
      if(g_lows[i]<lo) lo=g_lows[i];
   }
   return (hi>-DBL_MAX && lo<DBL_MAX && hi>lo);
}

void UpdateATR(const MqlRates &b)
{
   double tr=b.high-b.low;
   if(g_have_prev_close)
   {
      tr=MathMax(tr,MathAbs(b.high-g_prev_close));
      tr=MathMax(tr,MathAbs(b.low-g_prev_close));
   }
   if(!g_atr_init)
   {
      g_atr=tr;
      g_atr_init=true;
   }
   else
   {
      g_atr=((13.0/14.0)*g_atr)+((1.0/14.0)*tr);
   }
   g_tr_count++;
}

double NetForPosition(const long pos_id,double &exit_price)
{
   double net=0.0;
   exit_price=0.0;
   if(!HistorySelect(g_entry_time-3600,TimeCurrent()+3600)) return 0.0;
   int n=HistoryDealsTotal();
   for(int i=0;i<n;i++)
   {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0) continue;
      if((long)HistoryDealGetInteger(ticket,DEAL_MAGIC)!=MAGIC) continue;
      if((long)HistoryDealGetInteger(ticket,DEAL_POSITION_ID)!=pos_id) continue;
      net+=HistoryDealGetDouble(ticket,DEAL_PROFIT);
      net+=HistoryDealGetDouble(ticket,DEAL_COMMISSION);
      net+=HistoryDealGetDouble(ticket,DEAL_SWAP);
      net+=HistoryDealGetDouble(ticket,DEAL_FEE);
      long entry=(long)HistoryDealGetInteger(ticket,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
         exit_price=HistoryDealGetDouble(ticket,DEAL_PRICE);
   }
   return net;
}

void LogTrade(datetime exit_time,double exit_price,double net)
{
   if(g_fh==INVALID_HANDLE) return;
   FileWrite(g_fh,
      CANDIDATE_ID,
      TimeToString(g_signal_time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
      TimeToString(g_entry_time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
      TimeToString(exit_time,TIME_DATE|TIME_MINUTES|TIME_SECONDS),
      DoubleToString(g_entry_price,_Digits),
      DoubleToString(exit_price,_Digits),
      DoubleToString(net,8),
      DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),
      IntegerToString(HORIZON_BARS),
      DoubleToString(BUFFER_ATR,2));
   FileFlush(g_fh);
}

bool ClosePosition(datetime now)
{
   if(!g_in_trade) return true;
   if(!PositionSelect(_Symbol))
   {
      g_in_trade=false;
      return true;
   }
   if((long)PositionGetInteger(POSITION_MAGIC)!=MAGIC) return false;
   if(!g_trade.PositionClose(_Symbol))
   {
      g_order_failures++;
      PrintFormat("%s CLOSE FAIL ret=%u %s",CANDIDATE_ID,g_trade.ResultRetcode(),g_trade.ResultRetcodeDescription());
      return false;
   }
   double xp=0.0;
   double net=NetForPosition(g_position_id,xp);
   LogTrade(now,xp,net);
   g_exits++;
   g_in_trade=false;
   g_position_id=0;
   return true;
}

bool OpenLong(datetime signal_time,datetime entry_time)
{
   if(entry_time<ACTIVE_START || entry_time>=ACTIVE_END) return false;
   datetime due=entry_time + HORIZON_BARS*300;
   if(due>=ACTIVE_END) return false;
   g_trade.SetExpertMagicNumber(MAGIC);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   if(!g_trade.Buy(InpVolume,_Symbol,0.0,0.0,0.0,CANDIDATE_ID))
   {
      g_order_failures++;
      PrintFormat("%s BUY FAIL ret=%u %s",CANDIDATE_ID,g_trade.ResultRetcode(),g_trade.ResultRetcodeDescription());
      return false;
   }
   if(!PositionSelect(_Symbol))
   {
      g_order_failures++;
      return false;
   }
   g_signal_time=signal_time;
   g_entry_time=entry_time;
   g_exit_due=due;
   g_entry_price=PositionGetDouble(POSITION_PRICE_OPEN);
   g_position_id=(long)PositionGetInteger(POSITION_IDENTIFIER);
   g_in_trade=true;
   g_entries++;
   return true;
}

void ProcessClosedM5(const MqlRates &b,datetime current_m1)
{
   double prior_hi=0.0, prior_lo=0.0;
   bool have_range=PriorRange(prior_hi,prior_lo);

   UpdateATR(b);

   bool signal=false;
   if(have_range && g_tr_count>=14)
   {
      MqlDateTime dt;
      TimeToStruct(b.time,dt);
      bool in_session=(dt.hour>=SESSION_START && dt.hour<SESSION_END);
      if(in_session && b.close>(prior_hi+BUFFER_ATR*g_atr))
         signal=true;
   }

   if(signal)
   {
      g_signals++;
      if(!g_in_trade)
         OpenLong(b.time,current_m1);
   }

   AppendHistory(b.high,b.low);
   g_prev_close=b.close;
   g_have_prev_close=true;
}

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER))
   {
      Print(CANDIDATE_ID+" REFUSED: Strategy Tester only.");
      return INIT_FAILED;
   }
   if(_Period!=PERIOD_M1)
   {
      Print(CANDIDATE_ID+" REFUSED: tester timeframe must be M1.");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(StringFind(_Symbol,"XAUUSD")<0)
   {
      Print(CANDIDATE_ID+" REFUSED: XAUUSD only.");
      return INIT_PARAMETERS_INCORRECT;
   }
   g_trade.SetExpertMagicNumber(MAGIC);
   string name=StringFormat("Guardian\\top2\\%s_%s_TRADES.csv",CANDIDATE_ID,CleanSymbol());
   g_fh=FileOpen(name,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,';');
   if(g_fh==INVALID_HANDLE)
   {
      PrintFormat("%s cannot open trade log err=%d",CANDIDATE_ID,GetLastError());
      return INIT_FAILED;
   }
   FileWrite(g_fh,"candidate_id","signal_time","entry_time","exit_time","entry_price","exit_price","net_account_currency","balance_after","horizon_m5_bars","buffer_atr");
   FileFlush(g_fh);
   g_last_m1=iTime(_Symbol,PERIOD_M1,0);
   g_last_m5=iTime(_Symbol,PERIOD_M5,0);
   PrintFormat("%s READY | Strategy Tester only | lookback=%d buffer=%.2f horizon=%d | active 2017-01-01..2026-08-01",CANDIDATE_ID,LOOKBACK_BARS,BUFFER_ATR,HORIZON_BARS);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime m1=iTime(_Symbol,PERIOD_M1,0);
   if(m1<=0 || m1==g_last_m1) return;
   g_last_m1=m1;

   if(g_in_trade && m1>=g_exit_due)
      ClosePosition(m1);

   datetime m5=iTime(_Symbol,PERIOD_M5,0);
   if(m5<=0 || m5==g_last_m5) return;
   g_last_m5=m5;

   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,1,bars)!=1) return;
   ProcessClosedM5(bars[0],m1);
}

void OnDeinit(const int reason)
{
   if(g_in_trade && TimeCurrent()>=ACTIVE_END-60)
      ClosePosition(TimeCurrent());
   if(g_fh!=INVALID_HANDLE)
   {
      FileFlush(g_fh);
      FileClose(g_fh);
      g_fh=INVALID_HANDLE;
   }
   PrintFormat("%s FINAL | signals=%I64d entries=%I64d exits=%I64d failures=%I64d balance=%.2f equity=%.2f",
      CANDIDATE_ID,g_signals,g_entries,g_exits,g_order_failures,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
}
