param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v5.py"
$code=@'
from pathlib import Path
import pandas as pd, numpy as np, json, time
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests")
V3B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v3"
OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v5"; OUTB.mkdir(parents=True,exist_ok=True)
CACHE=V3B/"cache5"; t0=time.time()

def status(out,stage,i,n,msg=""):
    e=time.time()-t0; eta=e/i*(n-i) if i else None
    d={"stage":stage,"done":i,"total":n,"pct":round(100*i/max(n,1),2),"elapsed_s":round(e,1),
       "eta_s":None if eta is None else round(eta,1),"message":msg,"updated_utc":datetime.now(timezone.utc).isoformat()}
    (out/"STATUS.json").write_text(json.dumps(d,indent=2))
    print(f"[GEF5] {stage:<18} {i}/{n} {d['pct']:6.2f}% | elapsed {e/60:5.1f}m | ETA {'--' if eta is None else f'{eta/60:.1f}m'} | {msg}",flush=True)

v3s=[]
for p in V3B.glob("GEF3-*"):
    r=p/"RUN_RECEIPT.json"
    if r.exists():
        j=json.loads(r.read_text())
        if j.get("status")=="COMPLETE" and not j.get("locked_oos_2023_2025_accessed") and not j.get("protected_2026_accessed"):
            v3s.append((p.stat().st_mtime,p))
if not v3s: raise SystemExit("No eligible V3")
V3=sorted(v3s)[-1][1]
rid="GEF5-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"); OUT=OUTB/rid; OUT.mkdir()
status(OUT,"LOAD",0,1,V3.name)

cross=pd.read_csv(V3/"AUTOPSY_cross_market_representatives.csv")
annual=pd.read_csv(V3/"AUTOPSY_local_annual_stability.csv")
TARGETS=["GBPUSD","XAUUSD","EURUSD"]
D={s:pd.read_parquet(CACHE/f"{s}_2010_2022.parquet").sort_index() for s in set(TARGETS)|set(cross.explain)|set(cross.target)}
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

# Freeze direction from Discovery only. Composite uses at most 3 strongest annual local + 3 strongest cross components.
frozen={}
for tgt in TARGETS:
    z=D[tgt]; parts=[]
    la=annual[annual.symbol==tgt].head(3)
    for _,r in la.iterrows():
        f=feat(z,r.feature)
        dmask=(z.index>="2010-01-01")&(z.index<="2013-12-31 23:59:59")
        y=np.log(z.close.shift(-max(1,int(r.h)//5))/z.close)
        ic=f[dmask].corr(y[dmask],method="spearman"); sign=1 if ic>0 else -1
        parts.append((f,sign,f"local:{r.feature}"))
    ca=cross[cross.target==tgt].sort_values("min_abs_ic",ascending=False).head(3)
    for _,r in ca.iterrows():
        x=D[r.explain]["r5"].reindex(z.index).shift(max(1,int(r.lag)//5))
        dmask=(z.index>="2010-01-01")&(z.index<="2013-12-31 23:59:59")
        y=np.log(z.close.shift(-max(1,int(r.h)//5))/z.close)
        ic=x[dmask].corr(y[dmask],method="spearman"); sign=1 if ic>0 else -1
        parts.append((x,sign,f"cross:{r.explain}@{int(r.lag)}"))
    # Signed percentile votes: positive score means forecast UP, direction fixed by Discovery.
    votes=[]
    for x,sg,nm in parts:
        p=x.rank(pct=True)-.5
        votes.append((sg*p).rename(nm))
    S=pd.concat(votes,axis=1).mean(axis=1)
    frozen[tgt]={"score":S,"parts":[p[2] for p in parts]}
status(OUT,"LOAD",1,1,"3 composites frozen from Discovery direction")

# Fixed policy, no threshold search: strongest quintile; non-overlap; holding horizons 5/15/30/60.
# Entry delays 0/5/10/15 are robustness, not optimization.
rows=[]; yearly=[]; total=len(TARGETS)*4*4; k=0
for tgt in TARGETS:
    z=D[tgt]; base=frozen[tgt]["score"]
    for h in [5,15,30,60]:
        hb=max(1,h//5)
        for delay in [0,5,10,15]:
            k+=1; db=delay//5
            score=base.shift(db)
            q=pd.DataFrame({"score":score,"close":z.close})
            # threshold frozen from Discovery score distribution only
            dm=(q.index>="2010-01-01")&(q.index<="2013-12-31 23:59:59")
            thr=float(q.loc[dm,"score"].abs().quantile(.80))
            elig=np.flatnonzero((q.score.abs()>=thr).fillna(False).to_numpy())
            # strictly non-overlapping entries: next signal only after previous holding window
            chosen=[]; last=-10**9
            for ix in elig:
                if ix>=last+hb:
                    chosen.append(ix); last=ix
            rec=[]
            for ix in chosen:
                ex=ix+hb
                if ex>=len(q): continue
                s=float(q.score.iloc[ix]); p0=float(q.close.iloc[ix]); p1=float(q.close.iloc[ex])
                if not np.isfinite(s*p0*p1) or p0<=0 or p1<=0: continue
                side=1 if s>0 else -1
                gross_bp=side*np.log(p1/p0)*10000
                rec.append((q.index[ix],gross_bp,side))
            tr=pd.DataFrame(rec,columns=["time","gross_bp","side"])
            if len(tr):
                tr["year"]=pd.to_datetime(tr.time).dt.year
                # Remove best 1% trades and best 5 trading days.
                cut=tr.gross_bp.quantile(.99); trim=tr[tr.gross_bp<=cut]
                day=tr.assign(day=pd.to_datetime(tr.time).dt.date).groupby("day").gross_bp.sum().sort_values(ascending=False)
                bestdays=set(day.head(5).index)
                nobest=tr[~pd.to_datetime(tr.time).dt.date.isin(bestdays)]
                eq=tr.gross_bp.cumsum(); dd=float((eq-eq.cummax()).min())
                mean=float(tr.gross_bp.mean()); med=float(tr.gross_bp.median()); hit=float((tr.gross_bp>0).mean())
                be=max(0.0,mean) # all-in round-trip cost budget in bp
                rows.append({"target":tgt,"h":h,"delay":delay,"threshold":thr,"trades":len(tr),
                    "trades_per_year":len(tr)/13,"gross_bp_trade":mean,"median_bp_trade":med,"hit_rate":hit,
                    "gross_total_bp":float(tr.gross_bp.sum()),"max_drawdown_bp":dd,
                    "trim_best1pct_bp_trade":float(trim.gross_bp.mean()),"remove_best5days_bp_trade":float(nobest.gross_bp.mean()),
                    "break_even_allin_cost_bp":be,"long_share":float((tr.side>0).mean()),
                    "components":";".join(frozen[tgt]["parts"])})
                for yr,g in tr.groupby("year"):
                    yearly.append({"target":tgt,"h":h,"delay":delay,"year":int(yr),"trades":len(g),
                                   "gross_bp_trade":float(g.gross_bp.mean()),"hit_rate":float((g.gross_bp>0).mean()),
                                   "gross_total_bp":float(g.gross_bp.sum())})
            status(OUT,"ECONOMIC",k,total,f"{tgt} h={h} d={delay}")

res=pd.DataFrame(rows); yr=pd.DataFrame(yearly)
res.to_csv(OUT/"economic_nonoverlap_summary.csv",index=False); yr.to_csv(OUT/"economic_year_by_year.csv",index=False)

# Predeclared diagnostic summary; not a promotion gate yet.
base=res[res.delay==0].copy()
base["positive_after_trim"]=base.trim_best1pct_bp_trade>0
base["positive_without_best5days"]=base.remove_best5days_bp_trade>0
base["positive_year_fraction"]=base.apply(lambda r: float((yr[(yr.target==r.target)&(yr.h==r.h)&(yr.delay==0)].gross_bp_trade>0).mean()),axis=1)
base.to_csv(OUT/"candidate_diagnostics.csv",index=False)

receipt={"run_id":rid,"status":"COMPLETE","source_v3_run":V3.name,"created_utc":datetime.now(timezone.utc).isoformat(),
"research_max":"2022-12-31","locked_oos_2023_2025_accessed":False,"protected_2026_accessed":False,
"targets":TARGETS,"direction_source":"Discovery 2010-2013 only","entry_policy":"fixed strongest 20% score; non-overlapping trades",
"economic_tests":len(res),"year_rows":len(yr),"errors":[],
"cost_definition":"break_even_allin_cost_bp is the maximum round-trip spread+commission+slippage budget implied by mean gross bp/trade; no broker cost was invented.",
"next_gate":"Review economic diagnostics. If credible, define defensible instrument-specific costs and freeze strategy plus PASS/FAIL criteria before locked OOS."}
(OUT/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
status(OUT,"COMPLETE",1,1,f"tests={len(res)}")
print("\n=== V5 RECEIPT ==="); print(json.dumps(receipt,indent=2))
print("\n=== V5 BASE ECONOMICS (DELAY 0) ===")
print(base[["target","h","trades","trades_per_year","gross_bp_trade","hit_rate","max_drawdown_bp","trim_best1pct_bp_trade","remove_best5days_bp_trade","break_even_allin_cost_bp","positive_year_fraction"]].to_string(index=False))
print("\nRUN:",OUT)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V5 compile failed"}
Write-Host "=== GUARDIAN EDGE FACTORY V5 ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V5 run failed"}
