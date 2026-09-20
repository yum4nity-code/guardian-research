param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Py=Join-Path $Root "DataLake\tools\guardian_edge_factory_v18_validation.py"
$code=@'
from pathlib import Path
import pandas as pd,numpy as np,json,time,hashlib
from datetime import datetime,timezone
ROOT=Path(r"D:\MT5_Backtests")
RAW=ROOT/"DataLake"/"raw"/"histdata"
V17B=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v17"
OUTB=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v18"
OUTB.mkdir(parents=True,exist_ok=True); started=time.time()

def prog(o,s,i,n,m=""):
    e=time.time()-started
    eta=e/i*(n-i) if i else 0
    print(f"[GEF18] {s:<18} {i}/{n} {100*i/n:6.2f}% | elapsed {e/60:.1f}m | ETA {eta/60:.1f}m | {m}",flush=True)
    (o/"STATUS.json").write_text(json.dumps({"stage":s,"done":i,"total":n,"pct":100*i/n,"elapsed_s":e,"eta_s":eta,"message":m},indent=2))

runs=sorted([p for p in V17B.glob("GEF17-*") if (p/"FREEZE_RECEIPT.json").exists()])
if not runs: raise RuntimeError("No V17 freeze found")
src=runs[-1]
freeze=json.loads((src/"FREEZE_RECEIPT.json").read_text())
if freeze.get("status")!="FROZEN_AWAITING_HUMAN_REVIEW": raise RuntimeError("Freeze status invalid")
manifest_path=src/"FROZEN_VALIDATION_CANDIDATES.csv"
sha=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
if sha!=freeze["candidate_manifest_sha256"]: raise RuntimeError("Frozen manifest hash mismatch")
F=pd.read_csv(manifest_path)
expected={("UDXUSD","ret_24b",240,.99),("XAGUSD","zret_12b",240,.975),("WTIUSD","ret_48b",60,.99)}
got={(r["market"],r["feature"],int(r["horizon_min"]),float(r["tail"])) for _,r in F.iterrows()}
if got!=expected: raise RuntimeError(f"Candidate definitions changed: {got}")

rid="GEF18-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
O=OUTB/rid; O.mkdir()
print("[GEF18] 1/5 20% verify immutable freeze")
prog(O,"VERIFY_FREEZE",1,5,sha[:16])

def load(m,years):
    ys=[]
    for y in years:
        p=RAW/m/"M1"/f"{m}_M1_{y}.parquet"
        if not p.exists(): continue
        d=pd.read_parquet(p)
        tc=next(c for c in d.columns if c.lower() in ("datetime","time","timestamp"))
        d.index=pd.to_datetime(d[tc])
        x=d[["open","high","low","close"]].sort_index()
        ys.append(x.resample("5min",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna())
    return pd.concat(ys).sort_index() if ys else None

def feat(d,name):
    c=d.close.astype(float); lr=np.log(c/c.shift(1)); n=int(name.split("_")[1][:-1])
    if name.startswith("ret_"): return np.log(c/c.shift(n))
    if name.startswith("zret_"): return (lr-lr.rolling(n,min_periods=n).mean())/lr.rolling(n,min_periods=n).std()
    if name.startswith("range_"):
        lo=c.rolling(n,min_periods=n).min(); hi=c.rolling(n,min_periods=n).max(); return (c-lo)/(hi-lo)
    if name.startswith("vol_"): return lr.rolling(n,min_periods=n).std()
    raise ValueError(name)

def fwd(c,h,delay=0):
    ent=c.reindex(c.index+pd.Timedelta(minutes=delay)); ex=c.reindex(c.index+pd.Timedelta(minutes=delay+h))
    ent.index=c.index; ex.index=c.index
    return np.log(ex/ent)*1e4

rows=[]
for i,r in F.reset_index(drop=True).iterrows():
    m=r["market"]; fn=r["feature"]; h=int(r["horizon_min"]); tail=float(r["tail"])
    pre=load(m,range(2010,2014))
    val=load(m,range(2018,2023))
    xp=feat(pre,fn)
    yp=fwd(pre.close,h,0)
    qp=pd.concat([xp,yp],axis=1).dropna(); qp.columns=["x","y"]
    thr=float(qp.x.abs().quantile(tail))
    rho=float(qp.corr(method="spearman").iloc[0,1]); s=1.0 if rho>=0 else -1.0

    xv=feat(val,fn)
    base=pd.DataFrame({"x":xv},index=val.index).dropna()
    mask=base.x.abs()>=thr
    sig=(s*np.sign(base.loc[mask,"x"]))

    def eval_delay(delay):
        y=fwd(val.close,h,delay)
        p=(sig*y.reindex(sig.index)).dropna()
        yrs=p.groupby(p.index.year).mean()
        return {"n":int(len(p)),"gross_bp":float(p.mean()),"hit":float((p>0).mean()),"posyears":float((yrs>0).mean()),"yearly":{int(k):float(v) for k,v in yrs.items()}}

    d0=eval_delay(0); d5=eval_delay(5); d15=eval_delay(15)

    # Tail robustness on validation, but threshold remains frozen from discovery.
    y0=fwd(val.close,h,0)
    p0=(sig*y0.reindex(sig.index)).dropna()
    if len(p0):
        bestn=max(1,int(len(p0)*.01))
        trim=p0.drop(p0.nlargest(bestn).index)
        day=p0.groupby(p0.index.floor("D")).sum()
        bestdays=set(day.nlargest(min(5,len(day))).index)
        no5=p0[~p0.index.floor("D").isin(bestdays)]
        trimv=float(trim.mean()) if len(trim) else float("nan")
        no5v=float(no5.mean()) if len(no5) else float("nan")
    else:
        trimv=no5v=float("nan")

    # Validation success is predeclared here: positive center, >=4/5 positive years,
    # positive under +5/+15m delay, and positive after removing five best days.
    passed=bool(d0["n"]>=500 and d0["gross_bp"]>0 and d0["posyears"]>=.80 and d5["gross_bp"]>0 and d15["gross_bp"]>0 and no5v>0)

    rows.append({"market":m,"feature":fn,"horizon_min":h,"tail":tail,"direction":int(s),"threshold_abs":thr,
                 "val_n":d0["n"],"val_gross_bp":d0["gross_bp"],"val_hit":d0["hit"],"val_posyears":d0["posyears"],
                 "val_yearly":json.dumps(d0["yearly"]),"delay5_gross":d5["gross_bp"],"delay15_gross":d15["gross_bp"],
                 "trim_best1pct":trimv,"remove_best5days":no5v,"validation_pass":passed})
    prog(O,"VALIDATION",i+1,len(F),f"{m} {fn} pass={passed}")

R=pd.DataFrame(rows)
R.to_csv(O/"VALIDATION_RESULTS.csv",index=False)
P=R[R.validation_pass].copy()
P.to_csv(O/"VALIDATION_PASSES.csv",index=False)

receipt={
    "run_id":rid,
    "status":"COMPLETE",
    "source_v17":src.name,
    "frozen_manifest_sha256":sha,
    "validation_period":"2018-01-01..2022-12-31",
    "candidate_definitions_changed":False,
    "locked_oos_2023_2025_accessed":False,
    "protected_2026_accessed":False,
    "candidates":len(R),
    "validation_passes":len(P),
    "pass_rule":"n>=500; gross>0; >=4/5 positive years; delay +5m and +15m remain positive; remove best 5 days remains positive",
    "note":"2018-2022 used exactly once as independent validation for the three frozen V17 candidates. No parameter retuning in validation.",
    "next_gate":"If any pass, STOP for human review before any 2023-2025 locked OOS access. If none pass, return to pre-2018 discovery; do not mine validation data.",
    "errors":[]
}
(O/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2))
prog(O,"COMPLETE",1,1,f"passes={len(P)}")
print("\n=== V18 RECEIPT ===");print(json.dumps(receipt,indent=2))
print("\n=== VALIDATION RESULTS ===");print(R.to_string(index=False))
print("\n=== VALIDATION PASSES ===");print(P[["market","feature","horizon_min","tail","val_gross_bp","val_hit","val_posyears","delay5_gross","delay15_gross","remove_best5days"]].to_string(index=False) if len(P) else "NONE")
print("\nRUN:",O)
'@
Set-Content $Py $code -Encoding UTF8
py -m py_compile $Py
if($LASTEXITCODE -ne 0){throw "V18 compile failed"}
Write-Host "=== GEF V18 - INDEPENDENT VALIDATION 2018-2022 ONLY ==="
Get-FileHash $Py -Algorithm SHA256 | Format-Table -AutoSize
py $Py
if($LASTEXITCODE -ne 0){throw "V18 run failed"}
