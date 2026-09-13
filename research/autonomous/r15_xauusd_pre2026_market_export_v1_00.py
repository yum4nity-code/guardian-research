#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

START=pd.Timestamp("2017-01-01T00:00:00Z")
END=pd.Timestamp("2026-01-01T00:00:00Z")

def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(tmp,path)

def hb(path,completed,total,stage,extra=None):
    if not path:return
    x={"completed":int(completed),"total":int(total),"stage":stage,"updated_at_utc":datetime.now(timezone.utc).isoformat()}
    if extra:x.update(extra)
    atomic_json(path,x)

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def normalize(arr,a,b):
    if arr is None or len(arr)==0: raise RuntimeError(f"no M1 data for {a}..{b}")
    z=pd.DataFrame(arr)
    if "time" not in z or "open" not in z: raise RuntimeError("MT5 rates missing time/open")
    z["server_epoch"]=pd.to_numeric(z["time"],errors="raise").astype("int64")
    z=z[(z.server_epoch>=int(a.timestamp()))&(z.server_epoch<int(b.timestamp()))].copy()
    keep=["server_epoch","open","high","low","close","tick_volume","spread","real_volume"]
    for c in keep:
        if c not in z:
            if c in ("tick_volume","spread","real_volume"): z[c]=0
            else: raise RuntimeError(f"MT5 rates missing {c}")
    z=z[keep].sort_values("server_epoch").drop_duplicates("server_epoch",keep="last")
    if (z.server_epoch>=int(END.timestamp())).any(): raise RuntimeError("protected 2026 row encountered")
    return z.reset_index(drop=True)

def month_windows(a,b):
    cur=a
    while cur<b:
        nxt=min(cur+pd.offsets.MonthBegin(1),b)
        if nxt<=cur:nxt=min(cur+pd.DateOffset(months=1),b)
        yield cur,nxt
        cur=nxt

def reconcile(exported,canonical_path):
    if not canonical_path:return None
    p=Path(canonical_path)
    if not p.exists(): raise RuntimeError(f"canonical overlap file missing: {p}")
    c=pd.read_csv(p)
    if "server_epoch" not in c.columns:
        if "time" in c.columns:
            c["server_epoch"]=(pd.to_datetime(c["time"],utc=True).astype("int64")//1_000_000_000).astype("int64")
        elif "server_time" in c.columns:
            c["server_epoch"]=(pd.to_datetime(c["server_time"],utc=True).astype("int64")//1_000_000_000).astype("int64")
        else: raise RuntimeError("canonical overlap has no resolvable timestamp")
    req={"server_epoch","open","high","low","close"}
    if not req.issubset(c.columns): raise RuntimeError("canonical overlap columns invalid")
    c=c[(pd.to_numeric(c.server_epoch,errors="raise")>=int(pd.Timestamp("2024-01-01T00:00:00Z").timestamp()))&
        (pd.to_numeric(c.server_epoch,errors="raise")<int(END.timestamp()))].copy()
    e=exported[(exported.server_epoch>=int(pd.Timestamp("2024-01-01T00:00:00Z").timestamp()))&(exported.server_epoch<int(END.timestamp()))]
    m=c[list(req)].merge(e[list(req)],on="server_epoch",how="left",suffixes=("_c","_e"),indicator=True)
    coverage=float((m["_merge"]=="both").mean()) if len(m) else 0.0
    mismatch=0
    both=m["_merge"]=="both"
    for col in ("open","high","low","close"):
        mismatch+=int((~np.isclose(pd.to_numeric(m.loc[both,col+"_c"],errors="coerce"),
                                  pd.to_numeric(m.loc[both,col+"_e"],errors="coerce"),
                                  rtol=0.0,atol=1e-8)).sum())
    if coverage<0.9999 or mismatch!=0:
        raise RuntimeError(f"canonical 2024-2025 reconciliation failed coverage={coverage:.8f} mismatch={mismatch}")
    return {"canonical_rows":int(len(c)),"matched_rows":int(both.sum()),"coverage":coverage,"mismatched_ohlc_cells":mismatch,"canonical_sha256":sha256(p)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--terminal-exe",required=True)
    ap.add_argument("--required-server",default="FundedNext-Server 2")
    ap.add_argument("--symbol",default="XAUUSD")
    ap.add_argument("--output-dir",required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--canonical-2024-2025")
    A=ap.parse_args()
    out=Path(A.output_dir); out.mkdir(parents=True,exist_ok=True)
    prog=Path(A.progress_file) if A.progress_file else None
    terminal=Path(A.terminal_exe)
    if not terminal.exists(): raise RuntimeError(f"terminal missing: {terminal}")

    import MetaTrader5 as mt5
    if not mt5.initialize(str(terminal),timeout=60000,portable=True):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        ai=mt5.account_info()
        if ai is None: raise RuntimeError(f"MT5 account unavailable: {mt5.last_error()}")
        if str(ai.server)!=A.required_server: raise RuntimeError(f"wrong MT5 server: {ai.server!r}")
        if not mt5.symbol_select(A.symbol,True): raise RuntimeError(f"cannot select {A.symbol}: {mt5.last_error()}")

        windows=list(month_windows(START,END))
        by_year={}; done=0
        for a,b in windows:
            hb(prog,done,len(windows),"export_m1",{"month":a.strftime("%Y-%m")})
            arr=mt5.copy_rates_range(A.symbol,mt5.TIMEFRAME_M1,a.to_pydatetime(),b.to_pydatetime())
            z=normalize(arr,a,b)
            for y,g in z.groupby(pd.to_datetime(z.server_epoch,unit="s",utc=True).dt.year):
                if int(y)>=2026: raise RuntimeError("protected 2026 year encountered")
                by_year.setdefault(int(y),[]).append(g.copy())
            done+=1

        meta={}
        full=[]
        for y in range(2017,2026):
            if y not in by_year: raise RuntimeError(f"missing entire year {y}")
            z=pd.concat(by_year[y],ignore_index=True).sort_values("server_epoch").drop_duplicates("server_epoch").reset_index(drop=True)
            if len(z)<150000: raise RuntimeError(f"too few M1 rows for {y}: {len(z)}")
            p=out/f"xauusd_m1_{y}.csv"; z.to_csv(p,index=False)
            meta[str(y)]={"path":str(p),"sha256":sha256(p),"rows":int(len(z)),"first_epoch":int(z.server_epoch.iloc[0]),"last_epoch":int(z.server_epoch.iloc[-1])}
            full.append(z)

        allz=pd.concat(full,ignore_index=True).sort_values("server_epoch").drop_duplicates("server_epoch").reset_index(drop=True)
        rec=reconcile(allz,A.canonical_2024_2025) if A.canonical_2024_2025 else None
        manifest={"schema":1,"phase":"r15-xauusd-pre2026-market-export","status":"PASS","server":str(ai.server),"company":str(ai.company),
                  "symbol":A.symbol,"window":{"start":START.isoformat(),"end_exclusive":END.isoformat()},
                  "protected_2026_opened":False,"read_only_market_access":True,"timeframes":{"M1":meta},
                  "reconciliation_2024_2025":rec,"generated_at_utc":datetime.now(timezone.utc).isoformat()}
        mp=out/"r15_xauusd_pre2026_market_manifest.json"; atomic_json(mp,manifest)
        hb(prog,len(windows),len(windows),"complete",{"status":"PASS","protected_2026_opened":False})
        print(json.dumps({"status":"PASS","manifest":str(mp),"years":"2017-2025","server":str(ai.server),"protected_2026_opened":False}))
        return 0
    finally:
        mt5.shutdown()

if __name__=="__main__": raise SystemExit(main())
