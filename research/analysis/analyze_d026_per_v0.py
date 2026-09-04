#!/usr/bin/env python3
"""
D026 PER V0 analyzer.

Predeclared analysis only:
- data integrity / counts
- fixed first-touch EV at +1R/+2R/+3R
- side/path/year splits
- 40% @ +1R + 60% BE runner to +2R/+3R
- same-M1 ambiguity excluded rather than resolved optimistically

No parameter optimization.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import pandas as pd
import numpy as np

def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")

def min_positive(series) -> int:
    vals = [int(x) for x in series if pd.notna(x) and int(x) > 0]
    return min(vals) if vals else 0

def any_yes(series) -> str:
    return "YES" if series.astype(str).str.upper().eq("YES").any() else "NO"

def event_level(trades: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    keys = ["session_id","event_id","symbol","side"]
    agg = {"mfe_r":"max","mae_r":"max"}
    for c in ["hit05_utc","hit1_utc","hit2_utc","hit3_utc","hit4_utc","hit5_utc","stop_utc","be_after1_utc"]:
        if c in outcomes.columns:
            agg[c] = min_positive
    for c in ["be_after1_ambiguous_same_m1","ambiguous_same_m1"]:
        if c in outcomes.columns:
            agg[c] = any_yes
    ev = outcomes.groupby(keys, as_index=False).agg(agg)
    keep = ["session_id","event_id","entry_utc","symbol","side","level_family","path","entry","sl","risk_price"]
    jt = trades[keep].drop_duplicates(["session_id","event_id"])
    ev = jt.merge(ev,on=keys,how="left")
    ev["entry_dt"] = pd.to_datetime(ev["entry_utc"], format="%Y.%m.%d %H:%M:%S")
    ev["year"] = ev["entry_dt"].dt.year
    return ev

def wilson(p: float, n: int, z: float=1.96):
    if n <= 0: return (float("nan"), float("nan"))
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half, center+half

def fixed_metric(sub: pd.DataFrame, r: int) -> dict:
    h=sub[f"hit{r}_utc"].fillna(0).astype("int64")
    st=sub["stop_utc"].fillna(0).astype("int64")
    amb=sub.get("ambiguous_same_m1",pd.Series("NO",index=sub.index)).astype(str).str.upper().eq("YES")
    win=(h>0)&((st==0)|(h<st))
    loss=(st>0)&((h==0)|(st<h))
    valid=(win|loss)&(~amb)
    n=int(valid.sum()); w=int((win&valid).sum())
    if n == 0:
        return {"n_total":len(sub),"n_resolved":0,"wins":0,"p":None,"ev":None,"ev_lo95":None,"ev_hi95":None}
    p=w/n; lo,hi=wilson(p,n)
    return {
        "n_total":len(sub),"n_resolved":n,"wins":w,"p":p,
        "ev":(r+1)*p-1,
        "ev_lo95":(r+1)*lo-1,
        "ev_hi95":(r+1)*hi-1,
    }

def partial_be_metric(sub: pd.DataFrame,target_r: int,partial: float=.40) -> dict:
    h1=sub["hit1_utc"].fillna(0).astype("int64")
    ht=sub[f"hit{target_r}_utc"].fillna(0).astype("int64")
    st=sub["stop_utc"].fillna(0).astype("int64")
    be=sub["be_after1_utc"].fillna(0).astype("int64")
    amb1=sub.get("ambiguous_same_m1",pd.Series("NO",index=sub.index)).astype(str).str.upper().eq("YES")
    amb2=sub.get("be_after1_ambiguous_same_m1",pd.Series("NO",index=sub.index)).astype(str).str.upper().eq("YES")
    amb=amb1|amb2
    loss=(st>0)&((h1==0)|(st<h1))
    win1=(h1>0)&((st==0)|(h1<st))
    target=win1&(ht>0)&((be==0)|(ht<be))
    befirst=win1&(be>0)&((ht==0)|(be<ht))
    tie=((h1>0)&(st>0)&(h1==st)) | (win1&(ht>0)&(be>0)&(ht==be))
    valid=(loss|target|befirst)&(~amb)&(~tie)
    pay=pd.Series(np.nan,index=sub.index,dtype=float)
    pay.loc[loss]=-1.0
    pay.loc[befirst]=partial
    pay.loc[target]=partial+(1-partial)*target_r
    vals=pay.loc[valid].dropna()
    return {
        "n_total":len(sub),"n_resolved":int(len(vals)),
        "coverage":float(len(vals)/len(sub)) if len(sub) else None,
        "losses":int((loss&valid).sum()),"be_first":int((befirst&valid).sum()),"target_first":int((target&valid).sum()),
        "ev":float(vals.mean()) if len(vals) else None
    }

def group_records(ev: pd.DataFrame, cols: list[str]) -> list[dict]:
    out=[]
    for keys,sub in ev.groupby(cols,dropna=False):
        if not isinstance(keys,tuple): keys=(keys,)
        rec={k:v for k,v in zip(cols,keys)}
        rec["n"]=len(sub)
        for r in (1,2,3):
            rec[f"tp{r}"]=fixed_metric(sub,r)
        out.append(rec)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trades",required=True)
    ap.add_argument("--outcomes",required=True)
    ap.add_argument("--events")
    ap.add_argument("--json-out")
    ap.add_argument("--md-out")
    args=ap.parse_args()

    trades=read_csv(args.trades)
    outcomes=read_csv(args.outcomes)
    ev=event_level(trades,outcomes)

    result={
        "schema":"D026_PER_V0_ANALYSIS_1",
        "n_trade_rows":int(len(trades)),
        "n_unique_events":int(len(ev)),
        "sessions":trades.groupby(["session_id","symbol"]).size().reset_index(name="n").to_dict("records"),
        "overall":group_records(ev,["symbol"]),
        "year":group_records(ev,["symbol","year"]),
        "side":group_records(ev,["symbol","year","side"]),
        "path":group_records(ev,["symbol","year","path"]),
        "management_40pct_at_1R_BE_runner":[]
    }
    for sym,sub in ev.groupby("symbol"):
        result["management_40pct_at_1R_BE_runner"].append({
            "symbol":sym,"to_2R":partial_be_metric(sub,2,.40),"to_3R":partial_be_metric(sub,3,.40)
        })

    if args.events:
        events=read_csv(args.events)
        result["event_rows"]=int(len(events))
        if "transition" in events:
            result["transition_counts"]=events.groupby(["session_id","symbol","transition"]).size().reset_index(name="n").to_dict("records")

    text=json.dumps(result,indent=2,default=str)
    if args.json_out: Path(args.json_out).write_text(text,encoding="utf-8")

    lines=["# D026 PER V0 automated diagnostic","",f"Unique signals: **{len(ev)}**",""]
    for rec in result["overall"]:
        lines.append(f"## {rec['symbol']}")
        lines.append("")
        lines.append("| target | resolved | EV | 95% EV interval |")
        lines.append("|---|---:|---:|---:|")
        for r in (1,2,3):
            m=rec[f"tp{r}"]
            lines.append(f"| +{r}R | {m['n_resolved']} | {m['ev']:+.3f}R | {m['ev_lo95']:+.3f} .. {m['ev_hi95']:+.3f}R |")
        mg=next(x for x in result["management_40pct_at_1R_BE_runner"] if x["symbol"]==rec["symbol"])
        lines.append("")
        lines.append(f"- 40%@1R + BE runner -> 2R: {mg['to_2R']['ev']:+.3f}R on {mg['to_2R']['n_resolved']} resolved paths.")
        lines.append(f"- 40%@1R + BE runner -> 3R: {mg['to_3R']['ev']:+.3f}R on {mg['to_3R']['n_resolved']} resolved paths.")
        lines.append("")
    md="\n".join(lines)
    if args.md_out: Path(args.md_out).write_text(md,encoding="utf-8")
    else: print(md)

if __name__=="__main__":
    main()
