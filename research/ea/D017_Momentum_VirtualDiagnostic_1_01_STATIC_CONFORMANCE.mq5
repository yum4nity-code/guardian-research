#property strict
#property version   "1.01"
#property description "D017 Momentum long-history virtual diagnostic 1.01 - static conformance, no orders"

// D017 Momentum diagnostic extracted from Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.
// Purpose: validate the intrinsic Momentum entry edge over long history without account/margin/lot/prop-firm state.
// Preserved for BTC/ETH: setup M5, macro H1 EMA200, ADX/ATR regime, crypto shock/extension gates,
// Donchian anti-breakout, EMA50 direction confirmation, quality filter, structural SL, spread/SL gate.
// Non-crypto support is included for later research (setup M15, macro H1, 07-17 session gate).
// Deliberately excluded: account drawdown, max positions, daily trade cap, news, cooldown-after-losses,
// lot/min-margin constraints, request budget and actual execution success.

input int  InpMaxHoldHours = 48;
input bool InpVerbose = false;
input bool InpUseProductionSessionGate = true;

// Frozen production parameters from D017 v11.16 MOMENTUM_PROD.
#define ATR_PERIOD 14
#define ADX_PERIOD 14
#define ADX_TREND 20.0
#define MACRO_EMA 200
#define CRYPTO_DIR_EMA 50
#define DONCHIAN_CRYPTO 72
#define DONCHIAN_CLASSIC 24
#define STRUCT_BUFFER_ATR 0.25
#define CRYPTO_SL_FLOOR_ATR 1.25
#define CRYPTO_SL_CAP_ATR 3.50
#define CLASSIC_SL_FLOOR_ATR 1.60
#define MAX_SPREAD_PCT_SL 12.0
#define MIN_ATR_PCT 0.03
#define MAX_ATR_PCT_CLASSIC 0.80
#define MAX_ATR_PCT_GOLD 1.50
#define MAX_ATR_PCT_CRYPTO 3.00
#define MAX_SIGNAL_CANDLE_ATR 1.50
#define CRYPTO_JUMP_ATR_RATIO 2.40
#define CRYPTO_JUMP_CANDLE_ATR 2.00
#define CRYPTO_PRE_ATR_RATIO 1.80
#define CRYPTO_PRE_CANDLE_ATR 1.60
#define CRYPTO_EXTENSION_ATR 3.00
#define CRYPTO_POST_SHOCK_BARS 2
#define CLASSIC_SESSION_START 7.0
#define CLASSIC_SESSION_END 17.0
#define MAX_TRACKED 1024

enum MarketClass { MC_CRYPTO=0, MC_FOREX, MC_GOLD, MC_OTHER };
enum MarketRegime { MR_TREND=0, MR_RANGE, MR_HIGH_VOL_TREND, MR_HIGH_VOL_RANGE, MR_LOW_VOL, MR_UNKNOWN };
enum CryptoRegime { CR_NORMAL=0, CR_PRE_SHOCK, CR_SHOCK, CR_POST_SHOCK };
enum Side { SIDE_BUY=1, SIDE_SELL=-1 };

struct VTrade
{
   bool active;
   string event_id;
   Side side;
   datetime entry_time;
   double entry;
   double stop;
   double risk;
   double mfe_r;
   double mae_r;
   datetime hit05,hit1,hit125,hit15,hit2,hit25,hit3,hit4,hit5;
   datetime stop_time,be1_time,be125_time;
   bool amb_stop_target,amb_be1,amb_be125;
   bool h1,h4,h8,h24,h48;
};

MarketClass g_class=MC_OTHER;
ENUM_TIMEFRAMES g_setup_tf=PERIOD_M5;
ENUM_TIMEFRAMES g_macro_tf=PERIOD_H1;
int g_atr=INVALID_HANDLE,g_adx=INVALID_HANDLE,g_macro_ema=INVALID_HANDLE,g_macro_atr=INVALID_HANDLE,g_dir_ema=INVALID_HANDLE;
datetime g_last_setup_open=0,g_last_m1_open=0,g_last_shock_bar=0;
long g_event_counter=0;
string g_session="";
VTrade g_trades[MAX_TRACKED];

bool Contains(string s,string needle){StringToUpper(s);StringToUpper(needle);return StringFind(s,needle)>=0;}

MarketClass DetectClass()
{
   string u=_Symbol; StringToUpper(u);
   if(StringFind(u,"BTC")>=0 || StringFind(u,"ETH")>=0 || StringFind(u,"SOL")>=0 || StringFind(u,"XRP")>=0 ||
      StringFind(u,"DOG")>=0 || StringFind(u,"ADA")>=0 || StringFind(u,"LNK")>=0 || StringFind(u,"LINK")>=0 ||
      StringFind(u,"LTC")>=0 || StringFind(u,"BCH")>=0 || StringFind(u,"DOT")>=0 || StringFind(u,"AVAX")>=0 ||
      StringFind(u,"XMR")>=0 || StringFind(u,"ETC")>=0 || StringFind(u,"DASH")>=0) return MC_CRYPTO;
   if(StringFind(u,"XAU")>=0 || StringFind(u,"GOLD")>=0) return MC_GOLD;
   string letters="";
   for(int i=0;i<StringLen(u);i++)
   {
      ushort c=StringGetCharacter(u,i);
      if(c>='A' && c<='Z') letters+=CharToString((uchar)c);
   }
   if(StringLen(letters)>=6) return MC_FOREX;
   return MC_OTHER;
}

string ClassName(){if(g_class==MC_CRYPTO)return "CRYPTO";if(g_class==MC_FOREX)return "FOREX";if(g_class==MC_GOLD)return "GOLD";return "OTHER";}

bool IsSupportedCryptoMajor()
{
   if(g_class!=MC_CRYPTO) return true;
   string u=_Symbol; StringToUpper(u);
   return (StringFind(u,"BTC")>=0 || StringFind(u,"ETH")>=0);
}

void EnsureFolder()
{
   FolderCreate("GuardianResearch",FILE_COMMON);
   FolderCreate("GuardianResearch\\D017Momentum",FILE_COMMON);
}
string EventsFile(){return "GuardianResearch\\D017Momentum\\d017_momentum_virtual_events.csv";}
string TradesFile(){return "GuardianResearch\\D017Momentum\\d017_momentum_virtual_trades.csv";}
string OutcomesFile(){return "GuardianResearch\\D017Momentum\\d017_momentum_virtual_outcomes.csv";}

void LogEvent(string event_id,string transition,Side side,datetime t,double atr,double adx,double atr_rel,double don_hi,double don_lo,double sl_dist,double spread_pct,string context)
{
   EnsureFolder();
   int h=FileOpen(EventsFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0) FileWrite(h,"session_id","event_id","time","symbol","strategy","side","transition","setup_tf","macro_tf","market_class","atr","adx","atr_rel","donchian_high","donchian_low","sl_dist","spread_pct_sl","context");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session,event_id,TimeToString(t,TIME_DATE|TIME_SECONDS),_Symbol,"D017_MOMENTUM",(side==SIDE_BUY?"BUY":"SELL"),transition,EnumToString(g_setup_tf),EnumToString(g_macro_tf),ClassName(),
             DoubleToString(atr,8),DoubleToString(adx,4),DoubleToString(atr_rel,5),DoubleToString(don_hi,_Digits),DoubleToString(don_lo,_Digits),DoubleToString(sl_dist,_Digits),DoubleToString(spread_pct,4),context);
   FileClose(h);
}

void LogTrade(VTrade &v,string context)
{
   EnsureFolder();
   int h=FileOpen(TradesFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0) FileWrite(h,"session_id","event_id","entry_utc","symbol","strategy","variant","side","leg","entry","sl","risk_price","signal_tf","context");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session,v.event_id,TimeToString(v.entry_time,TIME_DATE|TIME_SECONDS),_Symbol,"D017_MOMENTUM","V11_16_PROD_SIGNAL",(v.side==SIDE_BUY?"BUY":"SELL"),0,
             DoubleToString(v.entry,_Digits),DoubleToString(v.stop,_Digits),DoubleToString(v.risk,_Digits),EnumToString(g_setup_tf),context);
   FileClose(h);
}

void LogOutcome(VTrade &v,string horizon,datetime t)
{
   EnsureFolder();
   int h=FileOpen(OutcomesFile(),FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE,';');
   if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0) FileWrite(h,"session_id","event_id","utc_text","symbol","strategy","side","horizon","mfe_r","mae_r","hit05_utc","hit1_utc","hit125_utc","hit15_utc","hit2_utc","hit25_utc","hit3_utc","hit4_utc","hit5_utc","stop_utc","be_after1_utc","be_after125_utc","ambiguous_stop_target_m1","ambiguous_be1_m1","ambiguous_be125_m1");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,g_session,v.event_id,TimeToString(t,TIME_DATE|TIME_SECONDS),_Symbol,"D017_MOMENTUM",(v.side==SIDE_BUY?"BUY":"SELL"),horizon,DoubleToString(v.mfe_r,6),DoubleToString(v.mae_r,6),
             (long)v.hit05,(long)v.hit1,(long)v.hit125,(long)v.hit15,(long)v.hit2,(long)v.hit25,(long)v.hit3,(long)v.hit4,(long)v.hit5,(long)v.stop_time,(long)v.be1_time,(long)v.be125_time,
             (v.amb_stop_target?"YES":"NO"),(v.amb_be1?"YES":"NO"),(v.amb_be125?"YES":"NO"));
   FileClose(h);
}

double Buf(int h,int shift)
{
   if(h==INVALID_HANDLE)return EMPTY_VALUE;
   double x[1]; if(CopyBuffer(h,0,shift,1,x)!=1)return EMPTY_VALUE; return x[0];
}

bool RelativeATR(double &ratio)
{
   ratio=1.0; double cur=Buf(g_atr,1); if(cur==EMPTY_VALUE||cur<=0)return false;
   double hist[]; ArraySetAsSeries(hist,true); if(CopyBuffer(g_atr,0,2,30,hist)<30)return false;
   double sum=0;int n=0;for(int i=0;i<30;i++){if(hist[i]>0){sum+=hist[i];n++;}}
   if(n==0)return false; ratio=cur/(sum/n);return true;
}

MarketRegime Regime(double adx,double atr_rel)
{
   if(adx<=0)return MR_UNKNOWN; bool trend=adx>=ADX_TREND, high=atr_rel>=1.25, low=atr_rel<=0.80;
   if(trend&&high)return MR_HIGH_VOL_TREND; if(!trend&&high)return MR_HIGH_VOL_RANGE; if(trend)return MR_TREND; if(low)return MR_LOW_VOL; return MR_RANGE;
}

CryptoRegime GetCryptoRegime(double atr_rel,double candle_range_atr)
{
   datetime bar=iTime(_Symbol,g_setup_tf,1);
   if(atr_rel>=CRYPTO_JUMP_ATR_RATIO || candle_range_atr>=CRYPTO_JUMP_CANDLE_ATR){g_last_shock_bar=bar;return CR_SHOCK;}
   if(g_last_shock_bar>0)
   {
      int shift=iBarShift(_Symbol,g_setup_tf,g_last_shock_bar,true);
      if(shift>=0 && shift<=CRYPTO_POST_SHOCK_BARS)return CR_POST_SHOCK;
   }
   if(atr_rel>=CRYPTO_PRE_ATR_RATIO || candle_range_atr>=CRYPTO_PRE_CANDLE_ATR)return CR_PRE_SHOCK;
   return CR_NORMAL;
}

bool AllowedSession(datetime t)
{
   if(!InpUseProductionSessionGate || g_class==MC_CRYPTO)return true;
   MqlDateTime d;TimeToStruct(t,d);if(d.day_of_week==0||d.day_of_week==6)return false;
   double h=d.hour+d.min/60.0;if(d.day_of_week==5&&h>=20.0)return false;
   return (h>=CLASSIC_SESSION_START && h<CLASSIC_SESSION_END);
}

bool CryptoDirection(Side side)
{
   if(g_class!=MC_CRYPTO)return true;
   double e1=Buf(g_dir_ema,1),e3=Buf(g_dir_ema,3);if(e1==EMPTY_VALUE||e3==EMPTY_VALUE)return false;
   double c1=iClose(_Symbol,g_setup_tf,1),c2=iClose(_Symbol,g_setup_tf,2),l1=iLow(_Symbol,g_setup_tf,1),l3=iLow(_Symbol,g_setup_tf,3),h1=iHigh(_Symbol,g_setup_tf,1),h3=iHigh(_Symbol,g_setup_tf,3);
   if(side==SIDE_BUY)return (c1>e1 && e1>e3 && c1>c2 && l1>=l3);
   return (c1<e1 && e1<e3 && c1<c2 && h1<=h3);
}

double StructuralSLDistance(Side side,double entry,double atr,double structural)
{
   double s=(side==SIDE_BUY?entry-structural:structural-entry); if(s<=0)s=0.50*atr;
   double d=s+STRUCT_BUFFER_ATR*atr;
   double floor=(g_class==MC_CRYPTO?CRYPTO_SL_FLOOR_ATR*atr:CLASSIC_SL_FLOOR_ATR*atr);
   if(d<floor)d=floor;
   if(g_class==MC_CRYPTO){double cap=CRYPTO_SL_CAP_ATR*atr;if(d>cap)d=cap;}
   return d;
}

int FreeSlot(){for(int i=0;i<MAX_TRACKED;i++)if(!g_trades[i].active)return i;return -1;}

void CreateSignal(Side side,double atr,double adx,double atr_rel,double don_hi,double don_lo,double structural,string context)
{
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0||q.ask<=q.bid)return;
   double entry=(side==SIDE_BUY?q.ask:q.bid); double sl_dist=StructuralSLDistance(side,entry,atr,structural);
   double spread=q.ask-q.bid; double spread_pct=(sl_dist>0?100.0*spread/sl_dist:999999.0);
   string eid=StringFormat("D017M_%s_%I64d_%I64d",_Symbol,(long)TimeCurrent(),++g_event_counter);
   if(sl_dist<=0 || spread_pct>MAX_SPREAD_PCT_SL)
   {
      LogEvent(eid,"REJECT_SPREAD_OR_SL",side,TimeCurrent(),atr,adx,atr_rel,don_hi,don_lo,sl_dist,spread_pct,context);return;
   }
   int s=FreeSlot();if(s<0){LogEvent(eid,"REJECT_NO_SLOT",side,TimeCurrent(),atr,adx,atr_rel,don_hi,don_lo,sl_dist,spread_pct,context);return;}
   double raw_stop=(side==SIDE_BUY?entry-sl_dist:entry+sl_dist);
   double stop=NormalizeDouble(raw_stop,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   int stops_level=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double market_ref=(side==SIDE_BUY?q.bid:q.ask);
   double min_dist=stops_level*point;
   bool stop_valid=(point>0.0 && stop>0.0 && (side==SIDE_BUY ? market_ref-stop>=min_dist : stop-market_ref>=min_dist));
   if(!stop_valid)
   {
      LogEvent(eid,"REJECT_INVALID_BROKER_STOP",side,TimeCurrent(),atr,adx,atr_rel,don_hi,don_lo,sl_dist,spread_pct,context);return;
   }
   VTrade v;ZeroMemory(v);v.active=true;v.event_id=eid;v.side=side;v.entry_time=TimeCurrent();v.entry=entry;v.risk=sl_dist;v.stop=stop;
   g_trades[s]=v;LogEvent(eid,"VALID_SIGNAL",side,v.entry_time,atr,adx,atr_rel,don_hi,don_lo,sl_dist,spread_pct,context);LogTrade(g_trades[s],context);
   if(InpVerbose)Print("[D017M] ",eid," ",(side==SIDE_BUY?"BUY":"SELL")," entry=",DoubleToString(entry,_Digits)," SL=",DoubleToString(v.stop,_Digits));
}

void EvaluateMomentum()
{
   if(g_class==MC_CRYPTO && !IsSupportedCryptoMajor())
   {
      // The production altcoin branch also uses liquidity/BTC-context profiles. Keep this first diagnostic exact for BTC/ETH instead of approximating alts.
      return;
   }
   double atr=Buf(g_atr,1),adx=Buf(g_adx,1);if(atr==EMPTY_VALUE||adx==EMPTY_VALUE||atr<=0)return;
   double atr_rel=1.0;if(!RelativeATR(atr_rel))return;
   double c1=iClose(_Symbol,g_setup_tf,1),o1=iOpen(_Symbol,g_setup_tf,1),h1=iHigh(_Symbol,g_setup_tf,1),l1=iLow(_Symbol,g_setup_tf,1);
   double c2=iClose(_Symbol,g_setup_tf,2),o2=iOpen(_Symbol,g_setup_tf,2),h2=iHigh(_Symbol,g_setup_tf,2),l2=iLow(_Symbol,g_setup_tf,2);
   if(c1<=0||c2<=0)return;

   double macro_e1=Buf(g_macro_ema,1),macro_e4=Buf(g_macro_ema,4),macro_a=Buf(g_macro_atr,1);if(macro_e1==EMPTY_VALUE||macro_e4==EMPTY_VALUE||macro_a==EMPTY_VALUE||macro_a<=0)return;
   double slope=macro_e1-macro_e4; double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   bool bull=false,bear=false;
   if(g_class==MC_CRYPTO){double sn=slope/macro_a;bull=(c1>macro_e1 && sn>0.05);bear=(c1<macro_e1 && sn<-0.05);}
   else {bull=(c1>macro_e1 && slope>3*point);bear=(c1<macro_e1 && slope<-3*point);}

   MarketRegime mr=Regime(adx,atr_rel);bool trend=(mr==MR_TREND||mr==MR_HIGH_VOL_TREND);if(!trend)return;

   int dn=(g_class==MC_CRYPTO?DONCHIAN_CRYPTO:DONCHIAN_CLASSIC);int hi=iHighest(_Symbol,g_setup_tf,MODE_HIGH,dn,2),lo=iLowest(_Symbol,g_setup_tf,MODE_LOW,dn,2);if(hi<0||lo<0)return;
   double don_hi=iHigh(_Symbol,g_setup_tf,hi),don_lo=iLow(_Symbol,g_setup_tf,lo);

   double atr_pct=100.0*atr/c1;double max_atr=(g_class==MC_CRYPTO?MAX_ATR_PCT_CRYPTO:(g_class==MC_GOLD?MAX_ATR_PCT_GOLD:MAX_ATR_PCT_CLASSIC));
   if(atr_pct<MIN_ATR_PCT||atr_pct>max_atr)return;
   if((h1-l1)>MAX_SIGNAL_CANDLE_ATR*atr)return;
   if(!AllowedSession(TimeCurrent()))return;

   bool extended=false;CryptoRegime cr=CR_NORMAL;
   if(g_class==MC_CRYPTO)
   {
      double ema1=Buf(g_dir_ema,1);if(ema1==EMPTY_VALUE)return;extended=(MathAbs(c1-ema1)/atr>=CRYPTO_EXTENSION_ATR);
      double candle_atr=(h1-l1)/atr;cr=GetCryptoRegime(atr_rel,candle_atr);if(cr!=CR_NORMAL)return;
   }

   double body2=MathAbs(c2-o2);
   bool buy=bull && c2>o2 && body2>=0.70*atr && c1>c2 && c1>o1 && c1<don_hi && !extended;
   bool sell=bear && c2<o2 && body2>=0.70*atr && c1<c2 && c1<o1 && c1>don_lo && !extended;
   if(buy && CryptoDirection(SIDE_BUY))CreateSignal(SIDE_BUY,atr,adx,atr_rel,don_hi,don_lo,l2,StringFormat("body2=%.3fATR|regime=%d",body2/atr,(int)mr));
   if(sell && CryptoDirection(SIDE_SELL))CreateSignal(SIDE_SELL,atr,adx,atr_rel,don_hi,don_lo,h2,StringFormat("body2=%.3fATR|regime=%d",body2/atr,(int)mr));
}

void SetHit(VTrade &v,double r,datetime t)
{
   if(r==0.5&&v.hit05==0)v.hit05=t;else if(r==1.0&&v.hit1==0)v.hit1=t;else if(r==1.25&&v.hit125==0)v.hit125=t;else if(r==1.5&&v.hit15==0)v.hit15=t;else if(r==2.0&&v.hit2==0)v.hit2=t;else if(r==2.5&&v.hit25==0)v.hit25=t;else if(r==3.0&&v.hit3==0)v.hit3=t;else if(r==4.0&&v.hit4==0)v.hit4=t;else if(r==5.0&&v.hit5==0)v.hit5=t;
}
datetime GetHit(VTrade &v,double r){if(r==0.5)return v.hit05;if(r==1.0)return v.hit1;if(r==1.25)return v.hit125;if(r==1.5)return v.hit15;if(r==2.0)return v.hit2;if(r==2.5)return v.hit25;if(r==3.0)return v.hit3;if(r==4.0)return v.hit4;if(r==5.0)return v.hit5;return 0;}

void ProcessPath(VTrade &v,MqlRates &b,datetime t)
{
   datetime bc=b.time+60;if(bc<=v.entry_time||v.risk<=0)return;
   double fav=(v.side==SIDE_BUY?MathMax(0.0,b.high-v.entry):MathMax(0.0,v.entry-b.low))/v.risk;
   double adv=(v.side==SIDE_BUY?MathMax(0.0,v.entry-b.low):MathMax(0.0,b.high-v.entry))/v.risk;
   v.mfe_r=MathMax(v.mfe_r,fav);v.mae_r=MathMax(v.mae_r,adv);
   bool stop_cross=(v.stop_time==0 && (v.side==SIDE_BUY?b.low<=v.stop:b.high>=v.stop));
   bool new_target=false;double rr[9]={0.5,1.0,1.25,1.5,2.0,2.5,3.0,4.0,5.0};
   for(int i=0;i<9;i++)if(GetHit(v,rr[i])==0){double px=(v.side==SIDE_BUY?v.entry+rr[i]*v.risk:v.entry-rr[i]*v.risk);bool cross=(v.side==SIDE_BUY?b.high>=px:b.low<=px);if(cross){SetHit(v,rr[i],t);new_target=true;}}
   bool hit1_this=(v.hit1==t),hit125_this=(v.hit125==t);
   if(v.be1_time==0 && v.hit1>0){bool cross=(v.side==SIDE_BUY?b.low<=v.entry:b.high>=v.entry);if(cross){v.be1_time=t;if(hit1_this)v.amb_be1=true;}}
   if(v.be125_time==0 && v.hit125>0){bool cross=(v.side==SIDE_BUY?b.low<=v.entry:b.high>=v.entry);if(cross){v.be125_time=t;if(hit125_this)v.amb_be125=true;}}
   if(stop_cross){v.stop_time=t;if(new_target)v.amb_stop_target=true;}
   long e=(long)(t-v.entry_time);
   if(!v.h1&&e>=3600){v.h1=true;LogOutcome(v,"1H",t);}if(!v.h4&&e>=14400){v.h4=true;LogOutcome(v,"4H",t);}if(!v.h8&&e>=28800){v.h8=true;LogOutcome(v,"8H",t);}if(!v.h24&&e>=86400){v.h24=true;LogOutcome(v,"24H",t);}if(!v.h48&&e>=InpMaxHoldHours*3600){v.h48=true;LogOutcome(v,StringFormat("%dH",InpMaxHoldHours),t);v.active=false;}
}

void ProcessM1()
{
   datetime o=iTime(_Symbol,PERIOD_M1,1);if(o<=0||o==g_last_m1_open)return;MqlRates b[1];if(CopyRates(_Symbol,PERIOD_M1,1,1,b)!=1)return;g_last_m1_open=o;datetime t=b[0].time+60;
   for(int i=0;i<MAX_TRACKED;i++)if(g_trades[i].active)ProcessPath(g_trades[i],b[0],t);
}

int OnInit()
{
   g_class=DetectClass();g_setup_tf=(g_class==MC_CRYPTO?PERIOD_M5:PERIOD_M15);g_macro_tf=PERIOD_H1;
   g_atr=iATR(_Symbol,g_setup_tf,ATR_PERIOD);g_adx=iADX(_Symbol,g_setup_tf,ADX_PERIOD);g_macro_ema=iMA(_Symbol,g_macro_tf,MACRO_EMA,0,MODE_EMA,PRICE_CLOSE);g_macro_atr=iATR(_Symbol,g_macro_tf,ATR_PERIOD);
   if(g_class==MC_CRYPTO)g_dir_ema=iMA(_Symbol,g_setup_tf,CRYPTO_DIR_EMA,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr==INVALID_HANDLE||g_adx==INVALID_HANDLE||g_macro_ema==INVALID_HANDLE||g_macro_atr==INVALID_HANDLE||(g_class==MC_CRYPTO&&g_dir_ema==INVALID_HANDLE))return INIT_FAILED;
   g_session=StringFormat("D017M100_%s_%I64d_%I64d",_Symbol,(long)TimeCurrent(),(long)GetTickCount64());EnsureFolder();
   for(int i=0;i<MAX_TRACKED;i++)g_trades[i].active=false;g_last_setup_open=iTime(_Symbol,g_setup_tf,0);g_last_m1_open=iTime(_Symbol,PERIOD_M1,1);
   Print("[D017M] START ",_Symbol," class=",ClassName()," setup=",EnumToString(g_setup_tf)," | NO ORDERS");return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){if(g_atr!=INVALID_HANDLE)IndicatorRelease(g_atr);if(g_adx!=INVALID_HANDLE)IndicatorRelease(g_adx);if(g_macro_ema!=INVALID_HANDLE)IndicatorRelease(g_macro_ema);if(g_macro_atr!=INVALID_HANDLE)IndicatorRelease(g_macro_atr);if(g_dir_ema!=INVALID_HANDLE)IndicatorRelease(g_dir_ema);}
void OnTick()
{
   ProcessM1();datetime cur=iTime(_Symbol,g_setup_tf,0);if(cur>0&&cur!=g_last_setup_open){g_last_setup_open=cur;EvaluateMomentum();}
}
