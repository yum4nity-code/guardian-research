param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v6.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests")
V3B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v3"
OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v6"; OUTB.mkdir(parents=True,exist_ok=True)
CACHE=V3B/"cache5"; t0=time.time()
TARGETS=["EURUSD","GBPUSD","XAUUSD"]; H=[5,15,30,60]
DISC0,DISC1="2010-01-01","2013-12-31 23:59:59"

def status(out,stage,i,n,msg=""):
    e=time.time()-t0; eta=e/i*(n-i) if i else None
    d={"stage":stage,"done":i,"total":n,"pct":round(100*i/max(n,1),2),"elapsed_s":round(e,1),
       "eta_s":None if eta is None else round(eta,1),"message":msg,"updated_utc":datetime.now(timezone.utc).isoformat()}
    (out/"STATUS.json").write_text(json.dumps(d,indent=2))
    print(f"[GEF6] {stage:<18} {i}/{n} {d['pct']:6.2f}% | elapsed {e/60:5.1f}m | ETA {'--' if eta is None else f'{eta/60:.1f}m'} | {msg}",flush=True)

v3s=[]
for p in V3B.glob("GEF3-*"):
    r=p/"RUN_RECEIPT.json"
    if r.exists():
        j=json.loads(r.read_text())
        if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"):
            v3s.append((p.stat().st_mtime,p))
if not v3s: raise SystemExit("No eligible V3")
V3=sorted(v3s)[-1][1]
rid="GEF6-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTB/rid; OUT.mkdir()
status(OUT,"LOAD",0,1,V3.name)

cross=pd.read_csv(V3/"AUTOPSY_cross_market_representatives.csv")
annual=pd.read_csv(V3/"AUTOPSY_local_annual_stability.csv")
need=set(TARGETS)|set(cross.target)|set(cross.explain)
D={s:pd.read_parquet(CACHE/f"{s}_2010_2022.parquet").sort_index() for s in need if (CACHE/f"{s}_2010_2022.parquet").exists()}
for s,z in D.items(): z.index=pd.to_datetime(z.index)

def feat(z,name):
    c=z.close; k=int(name.split("_")[-1]); b=max(1,k//5)
    if name.startswith("ret_"): return np.log(c/c.shift(b))
    if name.startswith("z_"):
        m=c.rolling(b,min_periods=max(3,b//4)).mean(); sd=c.rolling(b,min_periods=max(3,b//4)).std()
        return (c-m)/sd.replace(0,np.nan)
    if name.startswith("rangepos_"):
        lo=c.rolling(b,min_periods=max(3,b//4)).min(); hi=c.rolling(b,min_periods=max(3,b//4)).max()
        return (c-lo)/(hi-lo).replace(0,np.nan)
    return None

# Reconstruct V5 composite exactly, but preserve local and cross sleeves separately.
F={}
for tgt in TARGETS:
    z=D[tgt]; locals_,crosses=[],[]
    for _,r in annual[annual.symbol==tgt].head(3).iterrows():
        x=feat(z,r.feature); y=np.log(z.close.shift(-max(1,int(r.h)//5))/z.close)
        dm=(z.index>=DISC0)&(z.index<=DISC1); ic=x[dm].corr(y[dm],method="spearman"); sg=1 if ic>0 else -1
        locals_.append((sg*(x.rank(pct=True)-.5)).rename(str(r.feature)))
    for _,r in cross[cross.target==tgt].sort_values("min_abs_ic",ascending=False).head(3).iterrows():
        x=D[r.explain]["r5"].reindex(z.index).shift(max(1,int(r.lag)//5))
        y=np.log(z.close.shift(-max(1,int(r.h)//5))/z.close)
        dm=(z.index>=DISC0)&(z.index<=DISC1); ic=x[dm].corr(y[dm],method="spearman"); sg=1 if ic>0 else -1
        crosses.append((sg*(x.rank(pct=True)-.5)).rename(f"{r.explain}@{int(r.lag)}"))
    L=pd.concat(locals_,axis=1).mean(axis=1) if locals_ else pd.Series(index=z.index,dtype=float)
    C=pd.concat(crosses,axis=1).mean(axis=1) if crosses else pd.Series(index=z.index,dtype=float)
    ALL=pd.concat(locals_+crosses,axis=1).mean(axis=1)
    F[tgt]={"local":L,"cross":C,"all":ALL}
status(OUT,"LOAD",1,1,"V5 sleeves reconstructed")

# Mapping only: bins fixed from Discovery. No winner is selected here.
rows=[]; total=len(TARGETS)*len(H); k=0
for tgt in TARGETS:
    z=D[tgt]
    # realized-vol regime from trailing 60m returns, quantile edges learned in Discovery only
    rv=np.log(z.close).diff().rolling(12,min_periods=6).std()
    dm=(z.index>=DISC0)&(z.index<=DISC1)
    rv_edges=np.unique(rv[dm].dropna().quantile([0,.25,.5,.75,1]).to_numpy())
    for h in H:
        k+=1; hb=max(1,h//5); y=np.log(z.close.shift(-hb)/z.close)*10000
        score=F[tgt]["all"]; local=F[tgt]["local"]; crosss=F[tgt]["cross"]
        q=pd.DataFrame({"score":score,"local":local,"cross":crosss,"rv":rv,"y":y}).dropna(subset=["score","y"])
        d=q.loc[DISC0:DISC1]
        # conviction deciles: ABS score edges frozen from Discovery
        edges=np.unique(d.score.abs().quantile(np.linspace(0,1,11)).to_numpy())
        if len(edges)>2:
            q["conv_bin"]=pd.cut(q.score.abs(),bins=edges,include_lowest=True,duplicates="drop",labels=False)
            for b,g in q.groupby("conv_bin",observed=True):
                signed=np.sign(g.score)*g.y
                rows.append({"target":tgt,"h":h,"slice":"conviction_decile","bucket":int(b)+1,"n":len(g),
                             "gross_bp":float(signed.mean()),"median_bp":float(signed.median()),"hit":float((signed>0).mean())})
        # vol quartiles frozen Discovery
        if len(rv_edges)>2:
            q["vol_bin"]=pd.cut(q.rv,bins=rv_edges,include_lowest=True,duplicates="drop",labels=False)
            for b,g in q.groupby("vol_bin",observed=True):
                signed=np.sign(g.score)*g.y
                rows.append({"target":tgt,"h":h,"slice":"vol_quartile","bucket":int(b)+1,"n":len(g),
                             "gross_bp":float(signed.mean()),"median_bp":float(signed.median()),"hit":float((signed>0).mean())})
        # UTC hour map; descriptive, not optimized
        q["hour"]=q.index.hour
        for b,g in q.groupby("hour"):
            signed=np.sign(g.score)*g.y
            rows.append({"target":tgt,"h":h,"slice":"utc_hour","bucket":int(b),"n":len(g),
                         "gross_bp":float(signed.mean()),"median_bp":float(signed.median()),"hit":float((signed>0).mean())})
        # side asymmetry
        for nm,mask in [("long",q.score>0),("short",q.score<0)]:
            g=q[mask]; signed=np.sign(g.score)*g.y
            rows.append({"target":tgt,"h":h,"slice":"side","bucket":nm,"n":len(g),
                         "gross_bp":float(signed.mean()),"median_bp":float(signed.median()),"hit":float((signed>0).mean())})
        # local vs cross agreement: fixed sign relationship, no fitted threshold
        if q["local"].notna().any() and q["cross"].notna().any():
            agree=np.sign(q.local)==np.sign(q.cross)
            for nm,mask in [("agree",agree),("disagree",~agree)]:
                g=q[mask]; signed=np.sign(g.score)*g.y
                rows.append({"target":tgt,"h":h,"slice":"local_cross","bucket":nm,"n":len(g),
                             "gross_bp":float(signed.mean()),"median_bp":float(signed.median()),"hit":float((signed>0).mean())})
        status(OUT,"MAP",k,total,f"{tgt} h={h}")
pd.DataFrame(rows).to_csv(OUT/"expectancy_map.csv",index=False)

# Predeclared nested tail test: 80/90/95/97.5/99 percentiles ONLY, thresholds frozen in Discovery.
# This tests monotonicity / economic concentration; it does not choose a threshold.
tails=[]; yearly=[]; pcts=[.80,.90,.95,.975,.99]; total=len(TARGETS)*len(H)*len(pcts); k=0
for tgt in TARGETS:
    z=D[tgt]; score=F[tgt]["all"]; dm=(score.index>=DISC0)&(score.index<=DISC1)
    for h in H:
        hb=max(1,h//5); y=np.log(z.close.shift(-hb)/z.close)*10000
        for pct in pcts:
            k+=1; thr=float(score[dm].abs().quantile(pct))
            elig=np.flatnonzero((score.abs()>=thr).fillna(False).to_numpy())
            chosen=[]; last=-10**9
            for ix in elig:
                if ix>=last+hb: chosen.append(ix); last=ix
            rec=[]
            for ix in chosen:
                ex=ix+hb
                if ex>=len(z): continue
                s=float(score.iloc[ix]); ret=float(y.iloc[ix])
                if np.isfinite(s*ret): rec.append((z.index[ix],np.sign(s)*ret))
            tr=pd.DataFrame(rec,columns=["time","bp"])
            if len(tr):
                tr["year"]=pd.to_datetime(tr.time).dt.year
                cut=tr.bp.quantile(.99); trim=tr[tr.bp<=cut]
                day=tr.assign(day=pd.to_datetime(tr.time).dt.date).groupby("day").bp.sum().sort_values(ascending=False)
                nobest=tr[~pd.to_datetime(tr.time).dt.date.isin(set(day.head(5).index))]
                yrmeans=tr.groupby("year").bp.mean()
                tails.append({"target":tgt,"h":h,"pct":pct,"threshold":thr,"trades":len(tr),"trades_per_year":len(tr)/13,
                    "gross_bp_trade":float(tr.bp.mean()),"median_bp_trade":float(tr.bp.median()),"hit":float((tr.bp>0).mean()),
                    "trim_best1pct_bp_trade":float(trim.bp.mean()),"remove_best5days_bp_trade":float(nobest.bp.mean()),
                    "positive_year_fraction":float((yrmeans>0).mean()),"break_even_allin_cost_bp":max(0,float(tr.bp.mean()))})
                for yr,g in tr.groupby("year"):
                    yearly.append({"target":tgt,"h":h,"pct":pct,"year":int(yr),"trades":len(g),"gross_bp_trade":float(g.bp.mean())})
            status(OUT,"TAIL LADDER",k,total,f"{tgt} h={h} p={pct}")
T=pd.DataFrame(tails); T.to_csv(OUT/"tail_ladder.csv",index=False); pd.DataFrame(yearly).to_csv(OUT/"tail_yearly.csv",index=False)

# Gradient diagnostics only: increasing gross expectancy with conviction is evidence; no selected winner.
grad=[]
for (t,h),g in T.groupby(["target","h"]):
    g=g.sort_values("pct"); x=g.pct.to_numpy(); y=g.gross_bp_trade.to_numpy()
    grad.append({"target":t,"h":h,"n_levels":len(g),"gross_bp_at_80":float(g.iloc[0].gross_bp_trade),
                 "gross_bp_at_99":float(g.iloc[-1].gross_bp_trade),"monotone_steps":int(np.sum(np.diff(y)>=0)),
                 "spearman_pct_vs_bp":float(pd.Series(x).corr(pd.Series(y),method="spearman")),
                 "best1pct_trim_positive_at_99":bool(g.iloc[-1].trim_best1pct_bp_trade>0),
                 "positive_year_fraction_at_99":float(g.iloc[-1].positive_year_fraction)})
G=pd.DataFrame(grad); G.to_csv(OUT/"gradient_diagnostics.csv",index=False)

receipt={"run_id":rid,"status":"COMPLETE","source_v3_run":V3.name,"created_utc":datetime.now(timezone.utc).isoformat(),
"research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
"targets":TARGETS,"tail_percentiles":[80,90,95,97.5,99],"threshold_source":"Discovery 2010-2013 only",
"purpose":"Map expectancy concentration and test a predeclared nested conviction gradient; no sweet-zone winner is selected.",
"map_rows":len(rows),"tail_tests":len(T),"errors":[],
"next_gate":"Inspect monotonicity, tail economics, yearly stability and outlier sensitivity. Only then predeclare one or a very small number of strategy rules for final pre-OOS cost/delay/null confirmation."}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
status(OUT,"COMPLETE",1,1,f"map={len(rows)} tails={len(T)}")
print("\n=== V6 RECEIPT ==="); print(json.dumps(receipt,indent=2))
print("\n=== V6 CONVICTION GRADIENT ===")
print(G.to_string(index=False))
print("\n=== V6 TAIL LADDER ===")
print(T[["target","h","pct","trades_per_year","gross_bp_trade","hit","trim_best1pct_bp_trade","remove_best5days_bp_trade","positive_year_fraction","break_even_allin_cost_bp"]].to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V6 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V6 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V6 run failed"}
