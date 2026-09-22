from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import json
import math
import re
import hashlib
import time
import subprocess

ROOT=Path(r"D:\MT5_Backtests")
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97"
BASE.mkdir(parents=True,exist_ok=True)

ENGINE_VERSION="V97.0"
MIN_FAST_STATE=5000
OOS_START=pd.Timestamp("2023-01-01 00:00")
OOS_END=pd.Timestamp("2025-12-31 23:55")
HIST_PRE_END=pd.Timestamp("2022-12-31 23:55")

# Semantic bridge is frozen before any historical MT5 values are requested.
# Broker symbol spelling/suffix is discovered from the connected FTMO terminal itself.
SYMBOL_EXPECTED={
    "BCOUSD":"UKOIL.cash",
    "USDCHF":"USDCHF",
    "USDCAD":"USDCAD",
    "GBPUSD":"GBPUSD",
    "XAUUSD":"XAUUSD",
}
SYMBOL_ALIASES={
    "BCOUSD":["UKOIL.cash","UKOIL","BRENT.cash","BRENT","BRN.cash","BRN"],
    "USDCHF":["USDCHF"],
    "USDCAD":["USDCAD"],
    "GBPUSD":["GBPUSD"],
    "XAUUSD":["XAUUSD"],
}

BRIDGE_SPEC={
    "window":"2023-01-01 through 2025-12-31 only",
    "mt5_timeframe":"M1 fetched in UTC-bounded monthly chunks",
    "no_2026_market_values_requested":True,
    "semantic_symbol_expectation":SYMBOL_EXPECTED,
    "symbol_resolution":"verify FTMO terminal/account first, then resolve broker symbol name/suffix from symbols_get before requesting any history",
    "candidate_set":"exact V94 frozen 3",
    "checks":[
        "5m coverage and return concordance HistData vs FTMO MT5",
        "exact causal state agreement for every frozen feature",
        "joint signal Jaccard/precision/recall",
        "target-return concordance at common signal times",
        "historical MT5 spread distribution at frozen signal times",
    ],
    "important":"diagnostic only; no candidate can be removed or retuned by V97",
}

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def status(out,step,total_steps,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,"steps":total_steps,
        "percent":round(100*step/total_steps,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(
        f"[GEF97] {step}/{total_steps} {100*step/total_steps:.0f}% | {msg}"
        +(f" | {tail}" if tail else ""),
        flush=True,
    )

def causal_states(s,min_periods):
    s=pd.to_numeric(s,errors="coerce")
    mu=s.expanding(min_periods=min_periods).mean().shift(1)
    sd=s.expanding(min_periods=min_periods).std().shift(1).replace(0,np.nan)
    z=((s-mu)/sd).to_numpy(dtype=np.float64)
    finite=np.isfinite(z)
    return finite&(z<=-1.0),finite&(z>=1.0)

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

def load_histdata_m1(sym,years):
    parts=[]
    for year in years:
        if year>2025:
            raise RuntimeError("V97 refuses HistData 2026+")
        p=ROOT/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
        if not p.exists():
            raise RuntimeError(f"Missing HistData file {p}")
        d=pd.read_parquet(p)
        dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
        pc=next((c for c in d.columns if str(c).lower()=="close"),None)
        if dc is None and isinstance(d.index,pd.DatetimeIndex):
            d=d.reset_index(); dc=d.columns[0]
        if dc is None or pc is None:
            raise RuntimeError(f"Cannot identify datetime/close in {p}")
        # Existing Guardian convention for HistData: fixed EST -> UTC by +5h.
        utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
        q=pd.DataFrame({"utc":utc,"close":pd.to_numeric(d[pc],errors="coerce")}).dropna()
        q=q[(q["utc"]>=pd.Timestamp(f"{year}-01-01"))&(q["utc"]<pd.Timestamp(f"{year+1}-01-01"))]
        parts.append(q)
    q=pd.concat(parts,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    return q.set_index("utc")["close"]

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

def month_starts(start_year,end_year_inclusive):
    out=[]
    for y in range(start_year,end_year_inclusive+1):
        for m in range(1,13):
            a=pd.Timestamp(year=y,month=m,day=1,tz="UTC")
            if y==2025 and m==12:
                # Hard stop before protected 2026. copy_rates_range is inclusive.
                b=pd.Timestamp("2025-12-31 23:59:00",tz="UTC")
            elif m==12:
                b=pd.Timestamp(year=y+1,month=1,day=1,tz="UTC")
            else:
                b=pd.Timestamp(year=y,month=m+1,day=1,tz="UTC")
            out.append((a,b))
    return out

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

def _looks_ftmo(identity):
    txt=" ".join(str(identity.get(k) or "") for k in (
        "server","account_company","terminal_company","terminal_name","terminal_path"
    )).upper()
    return "FTMO" in txt

def _running_terminal_paths():
    cmd=[
        "powershell","-NoProfile","-Command",
        "(Get-Process terminal64 -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty Path | Sort-Object -Unique) -join [Environment]::NewLine"
    ]
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
        if p.returncode!=0:
            return []
        return [x.strip() for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []

def connect_ftmo_terminal(mt5,out):
    attempts=[]
    # First inspect whatever MetaTrader5.initialize() chooses by default.
    if mt5.initialize():
        ident=_identity(mt5)
        attempts.append({"mode":"default","path":None,**ident})
        if ident["connected"] and _looks_ftmo(ident):
            write_json(out/"MT5_TERMINAL_RESOLUTION.json",{
                "status":"FTMO_TERMINAL_RESOLVED",
                "selected":attempts[-1],
                "attempts":attempts,
            })
            return ident
        mt5.shutdown()

    # Known prior resolution: bind the Python API to the actual running broker terminal,
    # rather than assuming the default terminal process is the right one.
    for path in _running_terminal_paths():
        try:
            ok=mt5.initialize(path=path)
        except TypeError:
            ok=mt5.initialize(path)
        if not ok:
            attempts.append({"mode":"explicit_path","path":path,"initialize":False,"last_error":str(mt5.last_error())})
            mt5.shutdown()
            continue
        ident=_identity(mt5)
        attempts.append({"mode":"explicit_path","path":path,**ident})
        if ident["connected"] and _looks_ftmo(ident):
            write_json(out/"MT5_TERMINAL_RESOLUTION.json",{
                "status":"FTMO_TERMINAL_RESOLVED",
                "selected":attempts[-1],
                "attempts":attempts,
            })
            return ident
        mt5.shutdown()

    write_json(out/"MT5_TERMINAL_RESOLUTION.json",{
        "status":"FTMO_TERMINAL_NOT_FOUND",
        "selected":None,
        "attempts":attempts,
    })
    raise RuntimeError(
        "No connected FTMO MT5 terminal was found. Open/log in to the FTMO terminal and rerun. "
        "See MT5_TERMINAL_RESOLUTION.json for every terminal/account that was probed."
    )

def _norm_symbol(s):
    return re.sub(r"[^A-Z0-9]","",str(s).upper())

def resolve_broker_symbols(mt5,needed_source_markets,out):
    syms=mt5.symbols_get()
    if syms is None:
        raise RuntimeError(f"MT5 symbols_get() failed: {mt5.last_error()}")
    all_rows=[]
    by_name={}
    for s in syms:
        row={
            "name":str(s.name),
            "description":str(getattr(s,"description","") or ""),
            "path":str(getattr(s,"path","") or ""),
            "visible":bool(getattr(s,"visible",False)),
            "select":bool(getattr(s,"select",False)),
        }
        all_rows.append(row)
        by_name[row["name"]]=row

    resolved={}
    evidence={}
    for src in sorted(needed_source_markets):
        aliases=SYMBOL_ALIASES[src]
        # 1) Frozen exact aliases, ordered.
        exact=[a for a in aliases if a in by_name]

        # 2) Same semantic root with broker suffix/prefix punctuation.
        candidates=[]
        for row in all_rows:
            name=row["name"]
            norm=_norm_symbol(name)
            desc=(row["description"]+" "+row["path"]).upper()
            if src=="BCOUSD":
                ok=(
                    "UKOIL" in norm
                    or "BRENT" in norm
                    or "BRN"==norm
                    or "BRENT" in desc
                    or "UK OIL" in desc
                )
                bad=("WTI" in norm or "USOIL" in norm or "WTI" in desc or "WEST TEXAS" in desc)
                if ok and not bad:
                    candidates.append(row)
            else:
                root=_norm_symbol(aliases[0])
                if norm.startswith(root) or norm.endswith(root):
                    candidates.append(row)

        # De-duplicate while retaining deterministic name order.
        uniq={r["name"]:r for r in candidates}
        candidates=[uniq[k] for k in sorted(uniq)]

        if exact:
            chosen=exact[0]
            method="frozen_exact_alias"
        else:
            visible=[r["name"] for r in candidates if r["visible"]]
            selected=[r["name"] for r in candidates if r["select"]]
            names=[r["name"] for r in candidates]
            if len(selected)==1:
                chosen=selected[0]; method="unique_selected_semantic_match"
            elif len(visible)==1:
                chosen=visible[0]; method="unique_visible_semantic_match"
            elif len(names)==1:
                chosen=names[0]; method="unique_semantic_match"
            else:
                evidence[src]={
                    "expected":SYMBOL_EXPECTED[src],
                    "aliases":aliases,
                    "candidates":candidates,
                    "status":"AMBIGUOUS_OR_MISSING",
                }
                write_json(out/"MT5_SYMBOL_RESOLUTION.json",{
                    "status":"FAILED",
                    "resolved":resolved,
                    "evidence":evidence,
                })
                raise RuntimeError(
                    f"Cannot resolve broker symbol for {src}. "
                    f"Candidates={[r['name'] for r in candidates]}. "
                    "See MT5_SYMBOL_RESOLUTION.json; no history was requested."
                )

        if not mt5.symbol_select(chosen,True):
            raise RuntimeError(f"MT5 resolved symbol exists but symbol_select failed: {src}->{chosen}; last_error={mt5.last_error()}")
        resolved[src]=chosen
        evidence[src]={
            "expected":SYMBOL_EXPECTED[src],
            "aliases":aliases,
            "chosen":chosen,
            "method":method,
            "candidates":candidates,
            "status":"RESOLVED",
        }

    write_json(out/"MT5_SYMBOL_RESOLUTION.json",{
        "status":"RESOLVED_BEFORE_HISTORY",
        "resolved":resolved,
        "evidence":evidence,
    })
    return resolved

def fetch_mt5_m1(mt5,symbol):
    chunks=[]
    for i,(a,b) in enumerate(month_starts(2023,2025),1):
        rates=mt5.copy_rates_range(
            symbol,
            mt5.TIMEFRAME_M1,
            a.to_pydatetime(),
            b.to_pydatetime(),
        )
        if rates is None:
            raise RuntimeError(f"MT5 copy_rates_range returned None for {symbol} {a:%Y-%m}; last_error={mt5.last_error()}")
        if len(rates):
            d=pd.DataFrame(rates)
            d["utc"]=pd.to_datetime(d["time"],unit="s",utc=True).dt.tz_convert(None)
            chunks.append(d)
        if i%6==0:
            print(f"[GEF97] {symbol} MT5 history {i}/36 months",flush=True)
    if not chunks:
        raise RuntimeError(f"MT5 returned zero M1 bars for {symbol} 2023-2025")
    d=pd.concat(chunks,ignore_index=True).sort_values("utc").drop_duplicates("utc",keep="last")
    d=d[(d["utc"]>=OOS_START)&(d["utc"]<pd.Timestamp("2026-01-01"))].copy()
    if d.empty:
        raise RuntimeError(f"MT5 {symbol}: no 2023-2025 bars after UTC filter")
    if d["utc"].max()>=pd.Timestamp("2026-01-01"):
        raise RuntimeError(f"MT5 {symbol}: 2026 row leaked into V97")
    return d

def return_concordance(a,b,horizon_min):
    k=horizon_min//5
    ra=a/a.shift(k)-1.0
    rb=b/b.shift(k)-1.0
    q=pd.concat([ra.rename("hist"),rb.rename("ftmo")],axis=1).dropna()
    if len(q)<10:
        return {"n":len(q),"corr":np.nan,"median_abs_diff_bp":np.nan,"sign_agreement":np.nan}
    nz=(np.abs(q["hist"])>1e-12)|(np.abs(q["ftmo"])>1e-12)
    return {
        "n":int(len(q)),
        "corr":float(q["hist"].corr(q["ftmo"])),
        "median_abs_diff_bp":float(np.median(np.abs(q["hist"]-q["ftmo"]))*1e4),
        "sign_agreement":float((np.sign(q.loc[nz,"hist"])==np.sign(q.loc[nz,"ftmo"])).mean()) if nz.any() else np.nan,
    }

def target_return(px,mins):
    k=mins//5
    y=px.shift(-k)/px-1.0
    minute=(px.index.view("int64")//60_000_000_000).astype(np.int64)
    y[(minute%mins)!=0]=np.nan
    y[(px.index+pd.Timedelta(minutes=mins))>OOS_END]=np.nan
    return y

# ---------- exact V94 frozen panel ----------
runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v94").glob("GEF94-*"))
runs=[
    p for p in runs
    if (p/"RUN_RECEIPT.json").exists()
    and (p/"FINAL_2026_FORWARD_FREEZE.json").exists()
    and (p/"FROZEN_2026_FORWARD_PANEL.csv").exists()
]
if not runs:
    raise RuntimeError("No completed V94 freeze")
V94=runs[-1]
r94=json.loads((V94/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
frz94=json.loads((V94/"FINAL_2026_FORWARD_FREEZE.json").read_text(encoding="utf-8"))
panel_path=V94/"FROZEN_2026_FORWARD_PANEL.csv"
panel=pd.read_csv(panel_path)
if r94.get("status")!="COMPLETE_V94_PROMOTION_AND_2026_FREEZE":
    raise RuntimeError("V94 incomplete")
if r94.get("2026_values_accessed") or frz94.get("2026_values_accessed"):
    raise RuntimeError("2026 protection violated upstream")
if sha256(panel_path)!=frz94["panel_sha256"]:
    raise RuntimeError("V94 panel hash mismatch")
if len(panel)!=3:
    raise RuntimeError("V97 expects exact frozen 3")

V92=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v92"/r94["source_v92"]
r92=json.loads((V92/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V85=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v85"/r92["source_v85"]
design=json.loads((V85/"TRIAL_DESIGN.json").read_text(encoding="utf-8"))
state_meta=json.loads((V85/"STATE_CACHE_META.json").read_text(encoding="utf-8"))
catalog=pd.read_csv(V85/"FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
V84C=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v84c"/design["source_v84c"]
r84=json.loads((V84C/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
V83B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v83b"/r84["source_v83b"]
manifest=json.loads((V83B/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))
Fhist=pd.read_parquet(manifest["price_state_5m_path"])
Fhist.index=pd.to_datetime(Fhist.index)

RID="GEF97-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,12,"exact V94 frozen 3 loaded; V97 bridge spec not yet connected to MT5",source_v94=V94.name)

freeze={
    "run_id":RID,
    "status":"V97_FTMO_HISTORICAL_BRIDGE_SPEC_FROZEN",
    "source_v94":V94.name,
    "panel_sha256":frz94["panel_sha256"],
    "bridge_spec":BRIDGE_SPEC,
    "2026_values_accessed":False,
}
write_json(OUT/"V97_BRIDGE_FREEZE.json",freeze)
status(OUT,2,12,"FTMO semantic mapping and diagnostics physically frozen",symbols=SYMBOL_EXPECTED)

# ---------- resolve FTMO terminal + broker symbols BEFORE any historical values ----------
try:
    import MetaTrader5 as mt5
except Exception as e:
    raise RuntimeError(
        "Python package MetaTrader5 is unavailable. Install/use the same Python environment as the MT5 terminal. "
        f"Import error: {e!r}"
    )

needed_source_markets=set()
for r in panel.itertuples(index=False):
    needed_source_markets.add(feature_market(r.feature_i))
    needed_source_markets.add(feature_market(r.feature_j))
    needed_source_markets.add(target_market(r.target))
needed_source_markets.discard(None)
missing_map=sorted(needed_source_markets-set(SYMBOL_EXPECTED))
if missing_map:
    raise RuntimeError(f"No frozen FTMO semantic mapping for {missing_map}")

identity=connect_ftmo_terminal(mt5,OUT)
resolved_symbols=resolve_broker_symbols(mt5,needed_source_markets,OUT)
status(
    OUT,3,12,
    "correct FTMO terminal/account verified and broker symbols resolved before history",
    server=identity.get("server"),
    login=identity.get("login"),
    terminal_path=identity.get("terminal_path"),
    symbols=resolved_symbols,
)

ftmo_raw={}
try:
    for i,src in enumerate(sorted(needed_source_markets),1):
        ft=resolved_symbols[src]
        d=fetch_mt5_m1(mt5,ft)
        ftmo_raw[src]=d
        d.to_parquet(OUT/f"FTMO_{ft.replace('.','_')}_M1_2023_2025.parquet",index=False)
        print(f"[GEF97] MT5 {i}/{len(needed_source_markets)} {src}->{ft} rows={len(d)}",flush=True)
finally:
    mt5.shutdown()
status(OUT,4,12,"FTMO MT5 2023-2025 historical bars materialized; terminal disconnected",markets=len(ftmo_raw))

# ---------- HistData + 5m bridge ----------
hist_raw={}
hist5={}
ftmo5={}
spread5={}
market_rows=[]
for src in sorted(needed_source_markets):
    hist=load_histdata_m1(src,range(2023,2026))
    hist_raw[src]=hist
    h5=hist.resample("5min",label="right",closed="left").last().reindex(
        pd.date_range(OOS_START,OOS_END,freq="5min")
    )
    hist5[src]=h5

    d=ftmo_raw[src].copy().set_index("utc").sort_index()
    f5=d["close"].resample("5min",label="right",closed="left").last().reindex(h5.index)
    ftmo5[src]=f5
    sp=d["spread"].resample("5min",label="right",closed="left").last().reindex(h5.index)
    spread5[src]=sp

    overlap=pd.concat([h5.rename("hist"),f5.rename("ftmo")],axis=1).dropna()
    point=infer_point(d["close"])
    spread_bp=(sp*point/f5*1e4) if np.isfinite(point) else pd.Series(np.nan,index=f5.index)

    rec={
        "source_market":src,
        "ftmo_symbol":resolved_symbols[src],
        "hist_5m_nonnull":int(h5.notna().sum()),
        "ftmo_5m_nonnull":int(f5.notna().sum()),
        "overlap_5m":int(len(overlap)),
        "coverage_ftmo_vs_hist":float(len(overlap)/max(int(h5.notna().sum()),1)),
        "inferred_ftmo_point":float(point) if np.isfinite(point) else None,
        "spread_points_median":float(sp.dropna().median()) if sp.notna().any() else None,
        "spread_points_p95":float(sp.dropna().quantile(.95)) if sp.notna().any() else None,
        "spread_bp_median":float(spread_bp.dropna().median()) if spread_bp.notna().any() else None,
        "spread_bp_p95":float(spread_bp.dropna().quantile(.95)) if spread_bp.notna().any() else None,
    }
    for hm in (5,30,60,120,240):
        cc=return_concordance(h5,f5,hm)
        rec[f"ret{hm}_n"]=cc["n"]
        rec[f"ret{hm}_corr"]=cc["corr"]
        rec[f"ret{hm}_median_abs_diff_bp"]=cc["median_abs_diff_bp"]
        rec[f"ret{hm}_sign_agreement"]=cc["sign_agreement"]
    market_rows.append(rec)

M=pd.DataFrame(market_rows)
M.to_csv(OUT/"MARKET_FEED_CONCORDANCE.csv",index=False)
status(OUT,5,12,"HistData vs FTMO market-feed concordance computed",markets=len(M))

# ---------- exact mixed-feed causal state comparison ----------
needed_features=sorted(set(panel["feature_i"]).union(set(panel["feature_j"])))

# Build HistData 2014-2025 and FTMO 2023-2025 price frames.
pre_grid=pd.date_range("2014-01-01 00:00",HIST_PRE_END,freq="5min")
oos_grid=pd.date_range(OOS_START,OOS_END,freq="5min")
Ppre=pd.DataFrame(index=pd.date_range("2013-12-01 00:00",HIST_PRE_END,freq="5min"))
for src in sorted(needed_source_markets):
    s=load_histdata_m1(src,range(2013,2023))
    Ppre[src]=s.resample("5min",label="right",closed="left").last().reindex(Ppre.index)

Phist=pd.DataFrame(index=pd.date_range("2022-12-01 00:00",OOS_END,freq="5min"))
Pftmo=pd.DataFrame(index=Phist.index)
for src in sorted(needed_source_markets):
    # 2022 warmup from HistData for both, then source-specific 2023-25.
    warm=load_histdata_m1(src,[2022]).resample("5min",label="right",closed="left").last()
    hoos=hist5[src]
    foos=ftmo5[src]
    Phist[src]=pd.concat([warm,hoos]).sort_index().reindex(Phist.index)
    Pftmo[src]=pd.concat([warm,foos]).sort_index().reindex(Pftmo.index)

state_hist={}
state_ftmo={}
feature_rows=[]
for feat in needed_features:
    # Exact historical foundation 2010-2013 from V83B plus 2014-2022 rebuilt HistData.
    pre_ext=build_feature(feat,Ppre).reindex(pre_grid)
    foundation=pd.concat([
        pd.to_numeric(Fhist[feat],errors="coerce"),
        pd.to_numeric(pre_ext,errors="coerce"),
    ])

    hist_oos=build_feature(feat,Phist).reindex(oos_grid)
    ftmo_oos=build_feature(feat,Pftmo).reindex(oos_grid)

    hfull=pd.concat([foundation,pd.to_numeric(hist_oos,errors="coerce")])
    ffull=pd.concat([foundation,pd.to_numeric(ftmo_oos,errors="coerce")])
    hlo,hhi=causal_states(hfull,MIN_FAST_STATE)
    flo,fhi=causal_states(ffull,MIN_FAST_STATE)
    offset=len(foundation)
    h={"LO":hlo[offset:],"HI":hhi[offset:]}
    f={"LO":flo[offset:],"HI":fhi[offset:]}
    for st in ("LO","HI"):
        state_hist[(feat,st)]=h[st]
        state_ftmo[(feat,st)]=f[st]
        valid=np.isfinite(hist_oos.to_numpy(dtype=float))&np.isfinite(ftmo_oos.to_numpy(dtype=float))
        agree=float((h[st][valid]==f[st][valid]).mean()) if valid.any() else np.nan
        inter=int(np.count_nonzero(h[st]&f[st]&valid))
        union=int(np.count_nonzero((h[st]|f[st])&valid))
        feature_rows.append({
            "feature":feat,"state":st,
            "valid_rows":int(valid.sum()),
            "state_agreement":agree,
            "hist_state_rows":int(np.count_nonzero(h[st]&valid)),
            "ftmo_state_rows":int(np.count_nonzero(f[st]&valid)),
            "state_jaccard":float(inter/union) if union else np.nan,
        })

F=pd.DataFrame(feature_rows)
F.to_csv(OUT/"FEATURE_STATE_CONCORDANCE.csv",index=False)
status(OUT,6,12,"causal feature-state concordance computed",features=len(needed_features))

# ---------- frozen candidate signal + target concordance ----------
candidate_rows=[]
for r in panel.itertuples(index=False):
    A_h=state_hist[(r.feature_i,r.state_i)]
    B_h=state_hist[(r.feature_j,r.state_j)]
    A_f=state_ftmo[(r.feature_i,r.state_i)]
    B_f=state_ftmo[(r.feature_j,r.state_j)]
    J_h=A_h&B_h
    J_f=A_f&B_f

    mins=int(str(r.target).rsplit("_fwd_",1)[1].rstrip("m"))
    sample=((oos_grid.view("int64")//60_000_000_000)%mins)==0
    target_src=target_market(r.target)
    yh=target_return(hist5[target_src],mins).reindex(oos_grid)
    yf=target_return(ftmo5[target_src],mins).reindex(oos_grid)
    valid=sample&np.isfinite(yh.to_numpy(dtype=float))&np.isfinite(yf.to_numpy(dtype=float))
    sh=J_h&valid
    sf=J_f&valid
    inter=sh&sf
    union=sh|sf

    sign=1.0 if r.direction=="LONG" else -1.0
    q=pd.DataFrame({
        "hist":sign*yh.to_numpy(dtype=float),
        "ftmo":sign*yf.to_numpy(dtype=float),
    },index=oos_grid)
    q=q[inter].dropna()

    # Historical spread at FTMO signal timestamps. Spread field is bars-level, not tick slippage.
    d=ftmo_raw[target_src].set_index("utc").sort_index()
    point=infer_point(d["close"])
    f5=ftmo5[target_src]
    sp=spread5[target_src]
    spread_bp=(sp*point/f5*1e4) if np.isfinite(point) else pd.Series(np.nan,index=f5.index)
    sp_sig=spread_bp.reindex(oos_grid)[sf]

    candidate_rows.append({
        "development_rank":int(r.development_rank),
        "hypothesis":f"{r.feature_i} {r.state_i} AND {r.feature_j} {r.state_j} -> {r.direction} {r.target}",
        "hist_signal_n":int(sh.sum()),
        "ftmo_signal_n":int(sf.sum()),
        "common_signal_n":int(inter.sum()),
        "signal_union_n":int(union.sum()),
        "signal_jaccard":float(inter.sum()/union.sum()) if union.sum() else np.nan,
        "hist_signal_recall_on_ftmo":float(inter.sum()/sh.sum()) if sh.sum() else np.nan,
        "ftmo_signal_precision_vs_hist":float(inter.sum()/sf.sum()) if sf.sum() else np.nan,
        "common_signal_target_corr":float(q["hist"].corr(q["ftmo"])) if len(q)>=3 else np.nan,
        "hist_common_signal_mean_bp":float(q["hist"].mean()*1e4) if len(q) else np.nan,
        "ftmo_common_signal_mean_bp":float(q["ftmo"].mean()*1e4) if len(q) else np.nan,
        "median_ftmo_spread_bp_at_ftmo_signals":float(sp_sig.dropna().median()) if sp_sig.notna().any() else np.nan,
        "p95_ftmo_spread_bp_at_ftmo_signals":float(sp_sig.dropna().quantile(.95)) if sp_sig.notna().any() else np.nan,
        "spread_observations_at_signals":int(sp_sig.notna().sum()),
    })

C=pd.DataFrame(candidate_rows).sort_values("development_rank")
C.to_csv(OUT/"FROZEN_3_FTMO_SIGNAL_TARGET_BRIDGE.csv",index=False)
status(OUT,7,12,"frozen-3 signal/target bridge computed",candidates=len(C))

# ---------- explicit bridge diagnostics only ----------
diag=[]
for r in C.itertuples(index=False):
    diag.append({
        "development_rank":int(r.development_rank),
        "signal_jaccard":float(r.signal_jaccard),
        "common_signal_target_corr":float(r.common_signal_target_corr) if np.isfinite(r.common_signal_target_corr) else None,
        "median_spread_bp":float(r.median_ftmo_spread_bp_at_ftmo_signals) if np.isfinite(r.median_ftmo_spread_bp_at_ftmo_signals) else None,
        "note":"diagnostic only; V94 frozen panel unchanged and 2026 remains unopened",
    })
write_json(OUT/"BRIDGE_DIAGNOSTIC_FLAGS.json",diag)
status(OUT,8,12,"bridge diagnostics written; no candidate selection performed")

# ---------- no EIA/news filtering yet ----------
news_note={
    "rank3_target":"UKOIL.cash",
    "next_required_check":"FTMO Standard funded-account Crude Oil Inventories restriction, +/-2 minutes around release",
    "not_applied_in_v97":True,
    "reason":"first prove feed/signal/execution bridge before applying operational calendar exclusions",
}
write_json(OUT/"NEXT_NEWS_COMPLIANCE_CHECK.json",news_note)
status(OUT,9,12,"news-compliance step staged for V98, not applied to historical edge")

receipt={
    "run_id":RID,
    "status":"COMPLETE_V97_FTMO_HISTORICAL_BRIDGE",
    "engine_version":ENGINE_VERSION,
    "source_v94":V94.name,
    "frozen_2026_panel_sha256":frz94["panel_sha256"],
    "ftmo_symbols":resolved_symbols,
    "markets_bridged":len(M),
    "features_bridged":len(needed_features),
    "candidates_bridged":len(C),
    "candidate_set_changed":False,
    "thresholds_retuned":False,
    "2026_values_requested_or_stored":False,
    "next":"HUMAN_REVIEW_V97_THEN_V98_NEWS_AND_EXECUTION_SPEC; KEEP_2026_CLOSED",
}
write_json(OUT/"RUN_RECEIPT.json",receipt)
status(OUT,10,12,"receipt written")
status(OUT,11,12,"MT5 historical bridge complete; 2026 data never requested")
status(OUT,12,12,"DONE")

print("\n=== V97 RECEIPT ===")
print(json.dumps(receipt,indent=2))
print("\n=== V97 MARKET FEED CONCORDANCE ===")
show_m=[
    "source_market","ftmo_symbol","overlap_5m","coverage_ftmo_vs_hist",
    "ret5_corr","ret30_corr","ret60_corr","ret120_corr","ret240_corr",
    "spread_bp_median","spread_bp_p95",
]
print(M[show_m].to_string(index=False))
print("\n=== V97 FEATURE STATE CONCORDANCE ===")
print(F.to_string(index=False))
print("\n=== V97 FROZEN 3 FTMO SIGNAL/TARGET BRIDGE ===")
print(C.to_string(index=False))
print("\nRUN:",OUT)
