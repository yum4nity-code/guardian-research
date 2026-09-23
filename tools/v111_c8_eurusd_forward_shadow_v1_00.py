from __future__ import annotations
from pathlib import Path
import argparse, csv, json, time
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5

VERSION="V111-C8-EURUSD-FORWARD-SHADOW-1.0"
SYMBOL_BASE="EURUSD"
SOURCE_HOUR=11
FTMO_OFFSET_HOURS=2
ENTRY_HOUR_FTMO=(SOURCE_HOUR+FTMO_OFFSET_HOURS)%24
HOLD_MIN=120
COMMISSION_USD_PER_LOT_SIDE=2.5
CONTRACT_SIZE=100000.0

def utcnow(): return datetime.now(timezone.utc)

def resolve_symbol():
    if mt5.symbol_info(SYMBOL_BASE):
        mt5.symbol_select(SYMBOL_BASE,True); return SYMBOL_BASE
    c=[]
    for s in mt5.symbols_get() or []:
        u=s.name.upper()
        if u==SYMBOL_BASE: c.append((0,len(s.name),s.name))
        elif u.startswith(SYMBOL_BASE): c.append((1,len(s.name),s.name))
    if not c: raise RuntimeError("EURUSD not found in MT5")
    c.sort(); sym=c[0][2]; mt5.symbol_select(sym,True); return sym

def first_tick_at_or_after(sym, t):
    a=t
    b=t+timedelta(seconds=90)
    arr=mt5.copy_ticks_range(sym,a,b,mt5.COPY_TICKS_ALL)
    if arr is None or len(arr)==0: return None
    for x in arr:
        bid=float(x["bid"]); ask=float(x["ask"])
        if bid>0 and ask>0:
            ts=datetime.fromtimestamp(int(x["time_msc"])/1000.0,tz=timezone.utc)
            return {"time_utc":ts.isoformat(),"bid":bid,"ask":ask}
    return None

def load_state(p):
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"version":VERSION,"started_utc":utcnow().isoformat(),"last_completed_date":None,"open_trade":None}

def save_state(p,s):
    p.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8")

def append_csv(p,row):
    new=not p.exists()
    with p.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(row.keys()))
        if new:w.writeheader()
        w.writerow(row)

def commission_bp(entry_bid):
    return (2*COMMISSION_USD_PER_LOT_SIDE)/(entry_bid*CONTRACT_SIZE)*10000.0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\MT5_Backtests")
    ap.add_argument("--start-date",default=None,help="UTC YYYY-MM-DD; defaults to tomorrow UTC")
    ap.add_argument("--poll-seconds",type=int,default=15)
    a=ap.parse_args()

    root=Path(a.root)
    out=root/"Research"/"ForwardShadow"/"V111_C8_EURUSD"
    out.mkdir(parents=True,exist_ok=True)
    state_path=out/"STATE.json"
    ledger_path=out/"FORWARD_LEDGER.csv"
    log_path=out/"RUN.log"

    start_date=(datetime.fromisoformat(a.start_date).date() if a.start_date else (utcnow()+timedelta(days=1)).date())
    if start_date < utcnow().date():
        raise RuntimeError("Historical/backfill start date forbidden. Forward-only monitor refuses past dates.")

    if not mt5.initialize(): raise RuntimeError(f"MT5 init failed {mt5.last_error()}")
    try:
        ai=mt5.account_info()
        ident=" ".join(str(x or "") for x in [getattr(ai,"server",""),getattr(ai,"company",""),getattr(ai,"name","")])
        if "ftmo" not in ident.lower(): raise RuntimeError(f"FTMO guard failed: {ident}")
        sym=resolve_symbol()
        st=load_state(state_path)
        st["configured_start_date_utc"]=str(start_date)
        st["symbol"]=sym
        st["ftmo_identity"]=ident
        save_state(state_path,st)

        with log_path.open("a",encoding="utf-8") as lg:
            lg.write(f"{utcnow().isoformat()} START {VERSION} start={start_date} symbol={sym}\n")

        while True:
            now=utcnow()
            if now.date() < start_date:
                time.sleep(min(a.poll_seconds,60)); continue

            # Exclude weekends; exact calendar rule trades business days only.
            if now.weekday()>=5:
                time.sleep(min(a.poll_seconds,60)); continue

            entry_boundary=datetime(now.year,now.month,now.day,ENTRY_HOUR_FTMO,0,0,tzinfo=timezone.utc)
            exit_boundary=entry_boundary+timedelta(minutes=HOLD_MIN)
            ds=str(entry_boundary.date())

            # Enter at first tick at/after fixed boundary, never late by >90 sec.
            if st.get("open_trade") is None and st.get("last_completed_date")!=ds and entry_boundary <= now < entry_boundary+timedelta(seconds=90):
                en=first_tick_at_or_after(sym,entry_boundary)
                if en:
                    st["open_trade"]={"date":ds,"entry_boundary_utc":entry_boundary.isoformat(),
                                      "exit_boundary_utc":exit_boundary.isoformat(),**en}
                    save_state(state_path,st)

            ot=st.get("open_trade")
            if ot:
                xb=datetime.fromisoformat(ot["exit_boundary_utc"])
                if xb <= now < xb+timedelta(seconds=90):
                    ex=first_tick_at_or_after(sym,xb)
                    if ex:
                        entry_bid=float(ot["bid"]); exit_ask=float(ex["ask"])
                        gross_bp=(entry_bid-float(ex["bid"]))/entry_bid*10000.0
                        exec_bp=(entry_bid-exit_ask)/entry_bid*10000.0
                        comm=commission_bp(entry_bid)
                        net=exec_bp-comm
                        row={
                          "strategy":"V111_C8_EURUSD_H11_SHORT_120M",
                          "date":ot["date"],
                          "entry_boundary_utc":ot["entry_boundary_utc"],
                          "entry_time_utc":ot["time_utc"],
                          "entry_bid":entry_bid,
                          "entry_ask":float(ot["ask"]),
                          "exit_boundary_utc":ot["exit_boundary_utc"],
                          "exit_time_utc":ex["time_utc"],
                          "exit_bid":float(ex["bid"]),
                          "exit_ask":exit_ask,
                          "bid_gross_bp":gross_bp,
                          "observed_exec_bp":exec_bp,
                          "commission_bp":comm,
                          "net_after_commission_bp":net,
                          "live_order_sent":False
                        }
                        append_csv(ledger_path,row)
                        st["last_completed_date"]=ot["date"]
                        st["open_trade"]=None
                        save_state(state_path,st)
                        with log_path.open("a",encoding="utf-8") as lg:
                            lg.write(f"{utcnow().isoformat()} COMPLETE {json.dumps(row)}\n")
            time.sleep(a.poll_seconds)
    finally:
        mt5.shutdown()

if __name__=="__main__":
    main()
