from pathlib import Path
import pandas as pd
import numpy as np
import json
import math
import re
import hashlib
import time
import os
import subprocess

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v98_ftmo_corrected_bridge"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V98.0"
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=pd.Timestamp("2025-12-31 23:55")
MIN_FAST_STATE=5000
HORIZONS=(5,30,60,120,240)

# Exact semantic instruments for the corrected frozen ranks 7 and 9.
# DXY.cash is FTMO's Dollar Index symbol; terminal presence is verified before history.
FTMO_EXPECTED={
    "UDXUSD":"DXY.cash",
    "USDJPY":"USDJPY",
    "USDCHF":"USDCHF",
    "XAUUSD":"XAUUSD",
    "GBPUSD":"GBPUSD",
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def status(out,step,total,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,"steps":total,"percent":round(100*step/total,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF98] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

def feature_market(feature):
    m=re.match(r"price_([A-Z]+)_",str(feature))
    return m.group(1) if m else None

def target_market(target):
    return str(target).split("_fwd_",1)[0]

def build_feature(name,P):
    m=re.fullmatch(r"price_([A-Z]+)_ret_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_rv_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        r5=P[sym].pct_change(1,fill_method=None)
        return r5.rolling(k,min_periods=max(3,k//2)).std().astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_trend_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        return (P[sym]/P[sym].shift(k)-1).astype("float64")
    m=re.fullmatch(r"price_([A-Z]+)_zret_(\d+)m",name)
    if m:
        sym,mins=m.group(1),int(m.group(2)); k=mins//5
        r5=P[sym].pct_change(1,fill_method=None)
        mu=r5.rolling(k,min_periods=max(3,k//2)).mean()
        sd=r5.rolling(k,min_periods=max(3,k//2)).std().replace(0,np.nan)
        return ((r5-mu)/sd).astype("float64")
    raise RuntimeError(f"Unsupported feature {name}")

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float64)
    finite=np.isfinite(z)
    return finite&(z<=-1.0),finite&(z>=1.0)

def infer_point(close):
    x=pd.to_numeric(close,errors="coerce").dropna().to_numpy(dtype=np.float64)
    if len(x)<100:
        return np.nan
    sample=x[::max(1,len(x)//200000)]
    for digits in range(1,8):
        scale=10.0**digits
        err=np.abs(sample*scale-np.round(sample*scale))
        if float(np.mean(err<1e-6))>=0.999:
            return 1.0/scale
    return np.nan

def month_ranges():
    out=[]
    for y in (2023,2024,2025):
        for m in range(1,13):
            a=pd.Timestamp(year=y,month=m,day=1,tz="UTC")
            if y==2025 and m==12:
                b=pd.Timestamp("2025-12-31 23:59:00",tz="UTC")
            elif m==12:
                b=pd.Timestamp(year=y+1,month=1,day=1,tz="UTC")
            else:
                b=pd.Timestamp(year=y,month=m+1,day=1,tz="UTC")
            out.append((a,b))
    return out

def load_hist_raw(sym,years):
    parts=[]
    for year in years:
        if year>2025:
            raise RuntimeError("V98 refuses HistData 2026+")
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing HistData {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        cc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or cc is None:
            raise RuntimeError(f"Cannot identify datetime/close in {p}")
        q=pd.DataFrame({
            "stored_time":pd.to_datetime(d[dc],errors="coerce"),
            "close":pd.to_numeric(d[cc],errors="coerce"),
        }).dropna()
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("stored_time").drop_duplicates("stored_time",keep="last")
    return q.set_index("stored_time")["close"]

def hist_aligned(sym,years,shift_2023_map):
    raw=load_hist_raw(sym,years)
    # Years <=2022 use canonical HistData fixed EST -> UTC +300m.
    # 2023-2025 use frozen/validated source-time semantics.
    idx=raw.index
    shift=np.where(idx.year>=2023,int(shift_2023_map.get(sym,300)),300)
    s=pd.Series(raw.to_numpy(dtype=np.float64),index=idx+pd.to_timedelta(shift,unit="m"),name=sym)
    return s.sort_index().loc[~s.index.duplicated(keep="last")]

def corr_return(a,b,mins):
    k=mins//5
    ra=a/a.shift(k)-1.0
    rb=b/b.shift(k)-1.0
    q=pd.concat([ra.rename("a"),rb.rename("b")],axis=1).dropna()
    if len(q)<100:
        return {"n":len(q),"corr":np.nan,"mad_bp":np.nan,"sign":np.nan}
    nz=(np.abs(q["a"])>1e-12)|(np.abs(q["b"])>1e-12)
    return {
        "n":int(len(q)),
        "corr":float(q["a"].corr(q["b"])),
        "mad_bp":float(np.median(np.abs(q["a"]-q["b"]))*1e4),
        "sign":float((np.sign(q.loc[nz,"a"])==np.sign(q.loc[nz,"b"])).mean()) if nz.any() else np.nan,
    }

def target_return(px,mins):
    k=mins//5
    y=px.shift(-k)/px-1.0
    minute=(px.index.view("int64")//60_000_000_000).astype(np.int64)
    y[(minute%mins)!=0]=np.nan
    y[(px.index+pd.Timedelta(minutes=mins))>OOS_END]=np.nan
    return y

def _identity(mt5):
    ai=mt5.account_info()
    ti=mt5.terminal_info()
    return {
        "login":int(ai.login) if ai is not None else None,
        "server":str(ai.server) if ai is not None else None,
        "account_company":str(ai.company) if ai is not None else None,
        "terminal_company":str(ti.company) if ti is not None else None,
        "terminal_name":str(ti.name) if ti is not None else None,
        "terminal_path":str(ti.path) if ti is not None else None,
        "connected":bool(ti.connected) if ti is not None else False,
    }

def _looks_ftmo(ident):
    txt=" ".join(str(ident.get(k) or "") for k in ("server","account_company","terminal_company","terminal_name","terminal_path")).upper()
    return "FTMO" in txt

def connect_ftmo(mt5,terminal_exe,out):
    attempts=[]
    paths=[]
    if terminal_exe:
        paths.append(terminal_exe)
    env=os.environ.get("GEF_FTMO_TERMINAL","").strip()
    if env:
        paths.append(env)
    paths.append(r"C:\Program Files\MetaTrader 5\terminal64.exe")
    seen=set()
    paths=[p for p in paths if p and not (p.lower() in seen or seen.add(p.lower())) and Path(p).exists()]
    for path in paths:
        # Use the same order that successfully resolved V97.
        for portable in (True,False):
            try:
                ok=mt5.initialize(path=path,timeout=60000,portable=portable)
            except TypeError:
                ok=mt5.initialize(path,timeout=60000,portable=portable)
            if not ok:
                attempts.append({"path":path,"portable":portable,"ok":False,"error":str(mt5.last_error())})
                mt5.shutdown()
                continue
            ident=_identity(mt5)
            attempts.append({"path":path,"portable":portable,"ok":True,**ident})
            print(
                f"[GEF98] MT5 probe path={path} portable={portable} server={ident.get('server')} "
                f"login={ident.get('login')} connected={ident.get('connected')}",
                flush=True,
            )
            if ident["connected"] and _looks_ftmo(ident):
                write_json(out/"MT5_TERMINAL_RESOLUTION.json",{"selected":attempts[-1],"attempts":attempts})
                return ident
            mt5.shutdown()
    write_json(out/"MT5_TERMINAL_RESOLUTION.json",{"selected":None,"attempts":attempts})
    raise RuntimeError("No connected FTMO MT5 terminal found")

def resolve_symbols(mt5,out):
    syms=mt5.symbols_get()
    if syms is None:
        raise RuntimeError(f"symbols_get failed {mt5.last_error()}")
    by_name={str(s.name):s for s in syms}
    evidence={}
    resolved={}
    for src,expected in FTMO_EXPECTED.items():
        if expected in by_name:
            chosen=expected
            method="exact_expected"
        else:
            rows=[]
            for s in syms:
                name=str(s.name)
                desc=str(getattr(s,"description","") or "")
                path=str(getattr(s,"path","") or "")
                txt=(name+" "+desc+" "+path).upper()
                if src=="UDXUSD":
                    ok=("DXY" in txt or "DOLLAR INDEX" in txt or "US DOLLAR INDEX" in txt or "USDX" in txt)
                else:
                    ok=src in re.sub(r"[^A-Z0-9]","",name.upper())
                if ok:
                    rows.append({"name":name,"description":desc,"path":path})
            evidence[src]={"expected":expected,"candidates":rows}
            if len(rows)!=1:
                write_json(out/"MT5_SYMBOL_RESOLUTION.json",{"status":"FAILED","evidence":evidence})
                raise RuntimeError(f"Cannot uniquely resolve {src}; candidates={[x['name'] for x in rows]}")
            chosen=rows[0]["name"]
            method="unique_semantic_match"
        if not mt5.symbol_select(chosen,True):
            raise RuntimeError(f"symbol_select failed {src}->{chosen}: {mt5.last_error()}")
        resolved[src]=chosen
        evidence[src]={"expected":expected,"chosen":chosen,"method":method}
    write_json(out/"MT5_SYMBOL_RESOLUTION.json",{"status":"RESOLVED","resolved":resolved,"evidence":evidence})
    return resolved

def fetch_mt5(mt5,symbol):
    chunks=[]
    month_rows=[]
    for i,(a,b) in enumerate(month_ranges(),1):
        rates=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M1,a.to_pydatetime(),b.to_pydatetime())
        if rates is None:
            raise RuntimeError(f"copy_rates_range None {symbol} {a:%Y-%m}: {mt5.last_error()}")
        n=len(rates)
        month_rows.append({"month":a.strftime("%Y-%m"),"rows":int(n)})
        if n:
            d=pd.DataFrame(rates)
            d["utc"]=pd.to_datetime(d["time"],unit="s",utc=True).dt.tz_convert(None)
            chunks.append(d)
        if i%6==0:
            print(f"[GEF98] {symbol} history {i}/36 months",flush=True)
    if not chunks:
        raise RuntimeError(
            f"MT5 returned zero 2023-2025 bars for {symbol}. "
            "Open MT5 Symbols > Bars, request the available M1 history, then rerun V98."
        )
    d=pd.concat(chunks,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    d=d[(d["utc"]>=OOS_START)&(d["utc"]<pd.Timestamp("2026-01-01"))].copy()
    if d.empty or d["utc"].max()>=pd.Timestamp("2026-01-01"):
        raise RuntimeError(f"{symbol}: invalid bounded history")
    return d,month_rows

# ---------- corrected freeze / lineage preflight ----------
v97e_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97e_corrected_2026_freeze").glob("GEF97E-*"))
v97e_runs=[
    p for p in v97e_runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"CORRECTED_2026_FORWARD_PANEL.csv").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97E_CORRECTED_2026_FREEZE"
]
if not v97e_runs:
    raise RuntimeError("No completed V97E corrected freeze")
V97E=v97e_runs[-1]
r97e=json.loads((V97E/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
panel_path=V97E/"CORRECTED_2026_FORWARD_PANEL.csv"
panel=pd.read_csv(panel_path)
if sha256(panel_path)!=r97e["frozen_panel_sha256"]:
    raise RuntimeError("V97E panel hash mismatch")
if sorted(panel["development_rank"].astype(int).tolist())!=[7,9]:
    raise RuntimeError("V98 expects exact corrected frozen ranks [7,9]")
if r97e.get("2026_values_accessed"):
    raise RuntimeError("V97E reports 2026 access")

v97d=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97d_full_v93_repair"/r97e["source_v97d"]
corrected_scores=pd.read_csv(v97d/"CORRECTED_FULL_V93_SCORED_PANEL.csv")
expected_scores=corrected_scores[corrected_scores["development_rank"].astype(int).isin([7,9])].copy()
if len(expected_scores)!=2:
    raise RuntimeError("Missing corrected scores for ranks 7/9")

# V97B supplies the already-proven common FTMO feed timebase and USDCHF anomaly.
v97b_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97b_time_semantics").glob("GEF97B-*"))
v97b_runs=[
    p for p in v97b_runs
    if (p/"RUN_RECEIPT.json").exists()
    and json.loads((p/"RUN_RECEIPT.json").read_text(encoding="utf-8")).get("status")=="COMPLETE_V97B_SOURCE_TIME_SEMANTICS_FREEZE"
]
if not v97b_runs:
    raise RuntimeError("No completed V97B")
V97B=v97b_runs[-1]
r97b=json.loads((V97B/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
common_ftmo_shift=int(r97b["common_ftmo_index_shift_min"])
if r97b.get("storage_semantics_anomalies")!={"USDCHF":0}:
    raise RuntimeError("Unexpected V97B anomaly map")
if r97b.get("2026_accessed"):
    raise RuntimeError("V97B reports 2026 access")

# Existing proven source-time map plus yet-to-be-validated new markets.
shift_map={"USDCHF":0,"XAUUSD":300,"GBPUSD":300}

# Resolve original architecture for causal-state reconstruction.
v94_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
v94_runs=[p for p in v94_runs if (p/"RUN_RECEIPT.json").exists()]
if not v94_runs:
    raise RuntimeError("No V94 lineage")
V94=v94_runs[-1]
r94=json.loads((V94/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r94["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/r92["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))
Fhist=pd.read_parquet(manifest["price_state_5m_path"])
Fhist.index=pd.to_datetime(Fhist.index)

required_panel=["development_rank","feature_i","state_i","feature_j","state_j","target","direction"]
missing=[c for c in required_panel if c not in panel.columns]
if missing:
    raise RuntimeError(f"V97E panel missing {missing}")

needed_features=sorted(set(panel["feature_i"]).union(set(panel["feature_j"])))
needed_markets=set()
for row in panel.to_dict("records"):
    needed_markets.add(feature_market(row["feature_i"]))
    needed_markets.add(feature_market(row["feature_j"]))
    needed_markets.add(target_market(row["target"]))
needed_markets.discard(None)
if needed_markets!=set(FTMO_EXPECTED):
    raise RuntimeError(f"Unexpected corrected-panel market set {sorted(needed_markets)}")

RID="GEF98-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)

freeze={
    "run_id":RID,
    "status":"V98_CORRECTED_FTMO_BRIDGE_SPEC_FROZEN",
    "source_v97e":V97E.name,
    "frozen_panel_sha256":r97e["frozen_panel_sha256"],
    "frozen_ranks":[7,9],
    "ftmo_expected_symbols":FTMO_EXPECTED,
    "common_ftmo_index_shift_min_from_v97b":common_ftmo_shift,
    "new_histdata_semantics_to_validate":["USDJPY","UDXUSD"],
    "strategy_outcomes_used_for_time_alignment":False,
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "2026_accessed":False,
}
write_json(OUT/"V98_BRIDGE_FREEZE.json",freeze)
status(OUT,1,12,"corrected ranks 7/9 bridge spec frozen",source_v97e=V97E.name,markets=len(needed_markets))

# ---------- MT5 ----------
try:
    import MetaTrader5 as mt5
except Exception as e:
    raise RuntimeError(f"MetaTrader5 package unavailable: {e!r}")

terminal_exe=os.environ.get("GEF_FTMO_TERMINAL","").strip()
identity=connect_ftmo(mt5,terminal_exe,OUT)
resolved=resolve_symbols(mt5,OUT)
status(
    OUT,2,12,
    "FTMO terminal verified and exact/semantic symbols resolved",
    server=identity.get("server"),login=identity.get("login"),symbols=resolved,
)

ftmo_raw={}
history_meta={}
try:
    for i,src in enumerate(sorted(needed_markets),1):
        d,monthly=fetch_mt5(mt5,resolved[src])
        ftmo_raw[src]=d
        history_meta[src]={
            "symbol":resolved[src],
            "rows":int(len(d)),
            "first_utc":str(d["utc"].min()),
            "last_utc":str(d["utc"].max()),
            "months_with_rows":int(sum(x["rows"]>0 for x in monthly)),
            "month_rows":monthly,
        }
        d.to_parquet(OUT/f"FTMO_{resolved[src].replace('.','_')}_M1_2023_2025.parquet",index=False)
        print(
            f"[GEF98] MT5 {i}/{len(needed_markets)} {src}->{resolved[src]} rows={len(d)} "
            f"first={d['utc'].min()} last={d['utc'].max()}",
            flush=True,
        )
finally:
    mt5.shutdown()
write_json(OUT/"FTMO_HISTORY_AVAILABILITY.json",history_meta)
status(OUT,3,12,"bounded FTMO history materialized; terminal disconnected",markets=len(ftmo_raw))

# ---------- validate NEW HistData storage semantics independently of strategy PnL ----------
grid=pd.date_range(OOS_START,OOS_END,freq="5min")
sem_rows=[]
for src in ("USDJPY","UDXUSD"):
    fraw=ftmo_raw[src].set_index("utc")["close"].sort_index()
    f5=fraw.resample("5min",label="right",closed="left").last().reindex(grid)
    f5=f5.shift(common_ftmo_shift//5)

    raw=load_hist_raw(src,(2023,2024,2025))
    option=[]
    for storage_shift in (0,300):
        hs=raw.copy()
        hs.index=hs.index+pd.Timedelta(minutes=storage_shift)
        h5=hs.resample("5min",label="right",closed="left").last().reindex(grid)
        cors=[]
        row={
            "market":src,
            "histdata_stored_to_utc_shift_min":storage_shift,
            "ftmo_index_shift_min":common_ftmo_shift,
        }
        for hm in HORIZONS:
            c=corr_return(h5,f5,hm)
            row[f"ret{hm}_n"]=c["n"]
            row[f"ret{hm}_corr"]=c["corr"]
            row[f"ret{hm}_mad_bp"]=c["mad_bp"]
            row[f"ret{hm}_sign"]=c["sign"]
            if np.isfinite(c["corr"]):
                cors.append(c["corr"])
        row["mean_corr"]=float(np.mean(cors)) if cors else np.nan
        row["min_corr"]=float(np.min(cors)) if cors else np.nan
        option.append(row)
        sem_rows.append(row)

    opts=pd.DataFrame(option).sort_values(["mean_corr","min_corr"],ascending=[False,False])
    best=opts.iloc[0]
    if not np.isfinite(best["mean_corr"]):
        raise RuntimeError(f"{src}: no feed overlap to validate source-time semantics")
    if int(best["histdata_stored_to_utc_shift_min"])!=300:
        raise RuntimeError(
            f"{src}: source-time forensic contradicts canonical HistData +300m assumption. "
            f"Best={best.to_dict()}. STOP: V97D/V97E require another data repair."
        )
    # Operational equivalence gate. This is source validation, not strategy selection.
    if float(best["mean_corr"])<0.80 or float(best["min_corr"])<0.70:
        raise RuntimeError(
            f"{src}: canonical +300m time semantics selected, but feed equivalence is too weak "
            f"(mean_corr={best['mean_corr']:.3f}, min_corr={best['min_corr']:.3f})."
        )
    shift_map[src]=300
    print(
        f"[GEF98] source-time validated {src}: +300m | "
        f"mean_corr={best['mean_corr']:.4f} min_corr={best['min_corr']:.4f}",
        flush=True,
    )

SEM=pd.DataFrame(sem_rows)
SEM.to_csv(OUT/"NEW_MARKET_SOURCE_TIME_SEMANTICS.csv",index=False)
write_json(OUT/"CORRECTED_HISTDATA_TIME_MAP.json",{
    "2023_2025_stored_to_utc_shift_min":shift_map,
    "ftmo_index_shift_min":common_ftmo_shift,
    "selected_without_strategy_outcomes":True,
})
status(OUT,4,12,"USDJPY and UDXUSD source-time semantics validated before strategy bridge",map=shift_map)

# ---------- corrected HistData vs aligned FTMO market concordance ----------
hist5={}
ftmo5={}
spread5={}
market_rows=[]
for src in sorted(needed_markets):
    hs=hist_aligned(src,(2023,2024,2025),shift_map)
    h5=hs.resample("5min",label="right",closed="left").last().reindex(grid)
    hist5[src]=h5

    d=ftmo_raw[src].set_index("utc").sort_index()
    f5=d["close"].resample("5min",label="right",closed="left").last().reindex(grid)
    f5=f5.shift(common_ftmo_shift//5)
    ftmo5[src]=f5

    sp=d["spread"].resample("5min",label="right",closed="left").last().reindex(grid)
    sp=sp.shift(common_ftmo_shift//5)
    spread5[src]=sp

    point=infer_point(d["close"])
    spread_bp=(sp*point/f5*1e4) if np.isfinite(point) else pd.Series(np.nan,index=grid)
    rec={
        "source_market":src,
        "ftmo_symbol":resolved[src],
        "hist_nonnull":int(h5.notna().sum()),
        "ftmo_nonnull":int(f5.notna().sum()),
        "overlap_5m":int((h5.notna()&f5.notna()).sum()),
        "first_ftmo_utc":history_meta[src]["first_utc"],
        "last_ftmo_utc":history_meta[src]["last_utc"],
        "spread_bp_median":float(spread_bp.dropna().median()) if spread_bp.notna().any() else np.nan,
        "spread_bp_p95":float(spread_bp.dropna().quantile(.95)) if spread_bp.notna().any() else np.nan,
    }
    for hm in HORIZONS:
        cc=corr_return(h5,f5,hm)
        rec[f"ret{hm}_corr"]=cc["corr"]
        rec[f"ret{hm}_n"]=cc["n"]
        rec[f"ret{hm}_mad_bp"]=cc["mad_bp"]
        rec[f"ret{hm}_sign"]=cc["sign"]
    market_rows.append(rec)

M=pd.DataFrame(market_rows)
M.to_csv(OUT/"CORRECTED_MARKET_FEED_CONCORDANCE.csv",index=False)
status(OUT,5,12,"corrected HistData vs aligned FTMO market concordance computed",markets=len(M))

# ---------- exact causal state bridge ----------
pre_grid=pd.date_range("2014-01-01 00:00","2022-12-31 23:55",freq="5min")
pre_warm=pd.date_range("2013-12-01 00:00","2022-12-31 23:55",freq="5min")
oos_grid=grid

Ppre=pd.DataFrame(index=pre_warm)
for src in sorted(needed_markets):
    s=hist_aligned(src,range(2013,2023),shift_map)
    Ppre[src]=s.resample("5min",label="right",closed="left").last().reindex(pre_warm)

# 2022 HistData warmup + 2023-25 corrected HistData/FTMO.
bridge_grid=pd.date_range("2022-12-01 00:00",OOS_END,freq="5min")
Ph=pd.DataFrame(index=bridge_grid)
Pf=pd.DataFrame(index=bridge_grid)
for src in sorted(needed_markets):
    warm=hist_aligned(src,[2022],shift_map).resample("5min",label="right",closed="left").last()
    Ph[src]=pd.concat([warm,hist5[src]]).sort_index().reindex(bridge_grid)
    Pf[src]=pd.concat([warm,ftmo5[src]]).sort_index().reindex(bridge_grid)

state_h={}
state_f={}
feature_rows=[]
for feat in needed_features:
    pre=build_feature(feat,Ppre).reindex(pre_grid)
    foundation=pd.concat([
        pd.to_numeric(Fhist[feat],errors="coerce"),
        pd.to_numeric(pre,errors="coerce"),
    ])
    hf=build_feature(feat,Ph).reindex(oos_grid)
    ff=build_feature(feat,Pf).reindex(oos_grid)

    hfull=pd.concat([foundation,pd.to_numeric(hf,errors="coerce")])
    ffull=pd.concat([foundation,pd.to_numeric(ff,errors="coerce")])
    hlo,hhi=causal_states(hfull,MIN_FAST_STATE)
    flo,fhi=causal_states(ffull,MIN_FAST_STATE)
    off=len(foundation)
    for st,hv,fv in (("LO",hlo[off:],flo[off:]),("HI",hhi[off:],fhi[off:])):
        state_h[(feat,st)]=hv
        state_f[(feat,st)]=fv
        valid=np.isfinite(hf.to_numpy(dtype=float))&np.isfinite(ff.to_numpy(dtype=float))
        inter=int(np.count_nonzero(hv&fv&valid))
        union=int(np.count_nonzero((hv|fv)&valid))
        feature_rows.append({
            "feature":feat,"state":st,
            "valid_rows":int(valid.sum()),
            "state_agreement":float((hv[valid]==fv[valid]).mean()) if valid.any() else np.nan,
            "hist_state_rows":int(np.count_nonzero(hv&valid)),
            "ftmo_state_rows":int(np.count_nonzero(fv&valid)),
            "state_jaccard":float(inter/union) if union else np.nan,
        })

F=pd.DataFrame(feature_rows)
F.to_csv(OUT/"CORRECTED_FEATURE_STATE_CONCORDANCE.csv",index=False)
status(OUT,6,12,"causal feature-state bridge computed",features=len(needed_features))

# ---------- rank 7/9 signal + target bridge ----------
score_by={int(r["development_rank"]):r for r in expected_scores.to_dict("records")}
candidate_rows=[]
for row in panel.to_dict("records"):
    rank=int(row["development_rank"])
    J_h=state_h[(row["feature_i"],row["state_i"])]&state_h[(row["feature_j"],row["state_j"])]
    J_f=state_f[(row["feature_i"],row["state_i"])]&state_f[(row["feature_j"],row["state_j"])]

    mins=int(str(row["target"]).split("_fwd_",1)[1].rstrip("m"))
    sample=((oos_grid.view("int64")//60_000_000_000)%mins)==0
    full_h=J_h&sample
    full_f=J_f&sample
    inter_full=full_h&full_f
    union_full=full_h|full_f

    target_src=target_market(row["target"])
    yh=target_return(hist5[target_src],mins).reindex(oos_grid)
    yf=target_return(ftmo5[target_src],mins).reindex(oos_grid)
    target_valid=sample&np.isfinite(yh.to_numpy(dtype=float))&np.isfinite(yf.to_numpy(dtype=float))
    common_target=J_h&J_f&target_valid
    ftmo_target_signals=J_f&target_valid

    sign=1.0 if row["direction"]=="LONG" else -1.0
    q=pd.DataFrame({
        "hist":sign*yh.to_numpy(dtype=float),
        "ftmo":sign*yf.to_numpy(dtype=float),
    },index=oos_grid)
    q_common=q[common_target].dropna()
    q_ftmo=q[ftmo_target_signals].dropna()

    d=ftmo_raw[target_src].set_index("utc").sort_index()
    point=infer_point(d["close"])
    sp=spread5[target_src]
    f5=ftmo5[target_src]
    sp_bp=(sp*point/f5*1e4) if np.isfinite(point) else pd.Series(np.nan,index=oos_grid)
    sp_sig=sp_bp.reindex(oos_grid)[ftmo_target_signals]

    # HistData signal count with valid HistData target must reproduce corrected V97D n.
    hist_valid_only=sample&np.isfinite(yh.to_numpy(dtype=float))
    hist_scored_n=int(np.count_nonzero(J_h&hist_valid_only))
    expected_n=int(score_by[rank]["n"])
    if hist_scored_n!=expected_n:
        raise RuntimeError(
            f"Corrected HistData parity failed rank {rank}: got n={hist_scored_n}, expected V97D n={expected_n}"
        )

    candidate_rows.append({
        "development_rank":rank,
        "hypothesis":f"{row['feature_i']} {row['state_i']} AND {row['feature_j']} {row['state_j']} -> {row['direction']} {row['target']}",
        "corrected_hist_scored_n_parity":hist_scored_n,
        "hist_signal_n_full":int(full_h.sum()),
        "ftmo_signal_n_full":int(full_f.sum()),
        "common_signal_n_full":int(inter_full.sum()),
        "signal_union_n_full":int(union_full.sum()),
        "signal_jaccard_full":float(inter_full.sum()/union_full.sum()) if union_full.sum() else np.nan,
        "hist_signal_recall_on_ftmo_full":float(inter_full.sum()/full_h.sum()) if full_h.sum() else np.nan,
        "ftmo_signal_precision_vs_hist_full":float(inter_full.sum()/full_f.sum()) if full_f.sum() else np.nan,
        "target_market":target_src,
        "ftmo_target_symbol":resolved[target_src],
        "target_overlap_common_signal_n":int(common_target.sum()),
        "ftmo_target_available_signal_n":int(ftmo_target_signals.sum()),
        "common_target_return_corr":float(q_common["hist"].corr(q_common["ftmo"])) if len(q_common)>=3 else np.nan,
        "hist_common_target_mean_bp":float(q_common["hist"].mean()*1e4) if len(q_common) else np.nan,
        "ftmo_common_target_mean_bp":float(q_common["ftmo"].mean()*1e4) if len(q_common) else np.nan,
        "ftmo_all_available_signal_mean_bp":float(q_ftmo["ftmo"].mean()*1e4) if len(q_ftmo) else np.nan,
        "median_ftmo_spread_bp_at_available_signals":float(sp_sig.dropna().median()) if sp_sig.notna().any() else np.nan,
        "p95_ftmo_spread_bp_at_available_signals":float(sp_sig.dropna().quantile(.95)) if sp_sig.notna().any() else np.nan,
        "spread_observations_at_available_signals":int(sp_sig.notna().sum()),
        "target_ftmo_first_utc":history_meta[target_src]["first_utc"],
        "target_ftmo_last_utc":history_meta[target_src]["last_utc"],
    })

C=pd.DataFrame(candidate_rows).sort_values("development_rank").reset_index(drop=True)
C.to_csv(OUT/"CORRECTED_RANKS_7_9_FTMO_BRIDGE.csv",index=False)
status(OUT,7,12,"corrected ranks 7/9 signal/target bridge computed",candidates=len(C))

# ---------- operational diagnostics, not selection ----------
diag=[]
for row in C.to_dict("records"):
    diag.append({
        "development_rank":int(row["development_rank"]),
        "signal_jaccard_full":row["signal_jaccard_full"],
        "target_overlap_common_signal_n":int(row["target_overlap_common_signal_n"]),
        "common_target_return_corr":row["common_target_return_corr"],
        "median_spread_bp":row["median_ftmo_spread_bp_at_available_signals"],
        "target_history_first_utc":row["target_ftmo_first_utc"],
        "note":"execution/feed diagnostic only; corrected V97E candidate set remains frozen",
    })
write_json(OUT/"OPERATIONAL_DIAGNOSTICS.json",diag)
status(OUT,8,12,"operational diagnostics written; no strategy selection or retuning")

# Explicit note about DXY history availability from actual terminal data.
dxy_meta=history_meta["UDXUSD"]
write_json(OUT/"DXY_FTMO_HISTORY_NOTE.json",{
    "symbol":resolved["UDXUSD"],
    "actual_first_bar_utc":dxy_meta["first_utc"],
    "actual_last_bar_utc":dxy_meta["last_utc"],
    "months_with_rows_2023_2025":dxy_meta["months_with_rows"],
    "implication":"Rank 7 FTMO target-return bridge is limited to the period actually present in the FTMO terminal. This does not alter the HistData OOS edge result.",
})
status(OUT,9,12,"DXY target-history availability explicitly recorded")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V98_CORRECTED_FTMO_BRIDGE",
    "engine_version":ENGINE_VERSION,
    "source_v97e":V97E.name,
    "frozen_panel_sha256":r97e["frozen_panel_sha256"],
    "frozen_ranks":[7,9],
    "ftmo_symbols":resolved,
    "common_ftmo_index_shift_min":common_ftmo_shift,
    "histdata_time_map_2023_2025":shift_map,
    "rank7_dxy_actual_first_bar_utc":dxy_meta["first_utc"],
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "strategy_outcomes_used_for_time_alignment":False,
    "2026_values_requested_or_stored":False,
    "next":"HUMAN_REVIEW_V98; THEN FREEZE LIVE EXECUTION SPEC AND CURRENT FTMO COMPLIANCE FOR RANKS 7/9; KEEP_2026_CLOSED",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,10,12,"receipt written")
status(OUT,11,12,"2026 remained outside every HistData and MT5 request")
status(OUT,12,12,"DONE")

print("\n=== V98 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V98 NEW MARKET SOURCE-TIME SEMANTICS ===")
show_sem=["market","histdata_stored_to_utc_shift_min","ftmo_index_shift_min","mean_corr","min_corr"]
print(SEM[show_sem].sort_values(["market","mean_corr"],ascending=[True,False]).to_string(index=False))
print("\n=== V98 CORRECTED MARKET FEED CONCORDANCE ===")
show_m=["source_market","ftmo_symbol","first_ftmo_utc","overlap_5m","ret5_corr","ret30_corr","ret60_corr","ret120_corr","ret240_corr","spread_bp_median","spread_bp_p95"]
print(M[show_m].to_string(index=False))
print("\n=== V98 CORRECTED FEATURE STATE CONCORDANCE ===")
print(F.to_string(index=False))
print("\n=== V98 CORRECTED RANKS 7/9 FTMO BRIDGE ===")
print(C.to_string(index=False))
print("\nRUN:",OUT)
