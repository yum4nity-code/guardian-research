#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, subprocess, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def heartbeat(path: Path | None, completed: int, total: int, stage: str):
    if path:
        atomic_json(path, {"completed": int(completed), "total": int(total), "stage": stage, "updated_at_utc": datetime.now(timezone.utc).isoformat()})

def bh_adjust(rows, pkey="p", qkey="q"):
    valid=[(i,float(r[pkey])) for i,r in enumerate(rows) if r.get(pkey) is not None and math.isfinite(float(r[pkey]))]
    valid.sort(key=lambda x:x[1]); m=len(valid); prev=1.0
    for rank in range(m,0,-1):
        idx,p=valid[rank-1]; q=min(prev,p*m/rank,1.0); rows[idx][qkey]=q; prev=q
    for r in rows:r.setdefault(qkey,None)

def normal_p_two_sided(z):
    return math.erfc(abs(float(z))/math.sqrt(2.0)) if math.isfinite(float(z)) else 1.0

def continuous_test(values, mask):
    a=values[mask & np.isfinite(values)]; b=values[(~mask) & np.isfinite(values)]
    if len(a)<2 or len(b)<2:return None
    ma=float(np.mean(a)); mb=float(np.mean(b)); va=float(np.var(a,ddof=1)); vb=float(np.var(b,ddof=1)); se=math.sqrt(va/len(a)+vb/len(b))
    z=(ma-mb)/se if se>0 else 0.0
    return {"n_state":len(a),"n_comp":len(b),"effect":ma-mb,"state_mean":ma,"comp_mean":mb,"p":normal_p_two_sided(z)}
def binary_test(values, mask):
    finite=np.isfinite(values); a=values[mask & finite]; b=values[(~mask) & finite]
    if len(a)<2 or len(b)<2:return None
    pa=float(np.mean(a)); pb=float(np.mean(b)); pooled=(float(np.sum(a))+float(np.sum(b)))/(len(a)+len(b)); se=math.sqrt(max(0.0,pooled*(1-pooled)*(1/len(a)+1/len(b))))
    z=(pa-pb)/se if se>0 else 0.0
    return {"n_state":len(a),"n_comp":len(b),"effect":pa-pb,"state_mean":pa,"comp_mean":pb,"p":normal_p_two_sided(z)}

def wilder_atr(g):
    prev=g["close"].shift(1); tr=pd.concat([(g.high-g.low).abs(),(g.high-prev).abs(),(g.low-prev).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
def build_features(df):
    df=df.copy(); df["segment"]=(df.server_epoch.diff().fillna(300)!=300).cumsum(); gr=df.groupby("segment",group_keys=False)
    df["atr14"]=gr.apply(lambda g:wilder_atr(g),include_groups=False).reset_index(level=0,drop=True)
    atr=df.atr14
    for k in (1,3,12): df[f"ret{k}_atr"]=(df.close-gr.close.shift(k))/atr
    df["bar_range_atr"]=(df.high-df.low)/atr; df["body_atr"]=(df.close-df.open)/atr
    df["upper_wick_atr"]=(df.high-np.maximum(df.open,df.close))/atr; df["lower_wick_atr"]=(np.minimum(df.open,df.close)-df.low)/atr
    df["atr_slope3"]=atr/gr.atr14.shift(3)-1; df["atr_slope12"]=atr/gr.atr14.shift(12)-1
    roll_hi6=gr.high.rolling(6,min_periods=6).max().reset_index(level=0,drop=True); roll_lo6=gr.low.rolling(6,min_periods=6).min().reset_index(level=0,drop=True)
    df["compression6_atr"]=(roll_hi6-roll_lo6)/atr
    roll_hi24=gr.high.rolling(24,min_periods=24).max().reset_index(level=0,drop=True); roll_lo24=gr.low.rolling(24,min_periods=24).min().reset_index(level=0,drop=True)
    df["dist_high24_atr"]=(roll_hi24-df.close)/atr; df["dist_low24_atr"]=(df.close-roll_lo24)/atr
    vm=gr.tick_volume.rolling(48,min_periods=48).mean().reset_index(level=0,drop=True); vs=gr.tick_volume.rolling(48,min_periods=48).std().reset_index(level=0,drop=True)
    df["tickvol_z48"]=(df.tick_volume-vm)/vs.replace(0,np.nan); df["gap_atr"]=(df.open-gr.close.shift(1))/atr
    df["server_hour"]=pd.to_datetime(df.server_time,format="%Y.%m.%d %H:%M:%S").dt.hour; df["hour_block"]=(df.server_hour//4).astype(int)
    return df

def add_labels(df,horizons):
    seg=df.segment.to_numpy(); close=df.close.to_numpy(float); high=df.high.to_numpy(float); low=df.low.to_numpy(float); atr=df.atr14.to_numpy(float); n=len(df)
    for h in horizons:
        valid=np.arange(n)+h<n; idx=np.arange(n); future_idx=np.minimum(idx+h,n-1); valid &= seg==seg[future_idx]
        fwd=np.full(n,np.nan); fwd[valid]=(close[future_idx[valid]]-close[valid])/atr[valid]; df[f"fwd_ret_atr_h{h}"]=fwd
        maxh=np.full(n,-np.inf); minl=np.full(n,np.inf); first_up=np.full(n,np.inf); first_dn=np.full(n,np.inf)
        for k in range(1,h+1):
            sh=np.full(n,np.nan); sl=np.full(n,np.nan); sh[:-k]=high[k:]; sl[:-k]=low[k:]; same=np.zeros(n,bool); same[:-k]=seg[:-k]==seg[k:]
            up=same & np.isfinite(atr) & (sh>=close+atr); dn=same & np.isfinite(atr) & (sl<=close-atr)
            first_up[(first_up==np.inf)&up]=k; first_dn[(first_dn==np.inf)&dn]=k
            maxh=np.where(same,np.maximum(maxh,np.nan_to_num(sh,nan=-np.inf)),maxh); minl=np.where(same,np.minimum(minl,np.nan_to_num(sl,nan=np.inf)),minl)
        move=np.full(n,np.nan); move[valid]=((maxh[valid]>=close[valid]+atr[valid]) | (minl[valid]<=close[valid]-atr[valid])).astype(float); df[f"move_ge_1atr_h{h}"]=move
        upfirst=np.full(n,np.nan); eligible=valid & ((first_up<np.inf)|(first_dn<np.inf)) & (first_up!=first_dn); upfirst[eligible]=(first_up[eligible]<first_dn[eligible]).astype(float); df[f"up_first_1atr_h{h}"]=upfirst
    return df

def fit_cutpoints(s):
    x=s[np.isfinite(s.to_numpy(float))].to_numpy(float)
    if len(x)<100:return None
    q=np.quantile(x,[.2,.4,.6,.8])
    if len(np.unique(q))<4:return None
    return [float(v) for v in q]
def assign_q(s,cuts): return np.digitize(s.to_numpy(float),np.array(cuts),right=True)
def quarterly_signs(df, mask, col, outcome, sign, min_n):
    good=0; details={}
    for q in (1,2,3,4):
        qm=(df.quarter.to_numpy()==q); m=mask & qm
        res=continuous_test(df[col].to_numpy(float),m) if outcome=="mean_fwd_ret_atr" else binary_test(df[col].to_numpy(float),m)
        if res and res["n_state"]>=min_n:
            s=1 if res["effect"]>0 else (-1 if res["effect"]<0 else 0); same=s==sign; good += int(same); details[str(q)]={"effect":res["effect"],"n_state":res["n_state"],"same_sign":same}
        else: details[str(q)]={"insufficient":True}
    return good,details

def publish(publisher,status,summary,artifacts):
    if not publisher:return 0
    cmd=[sys.executable,str(publisher),"--phase","phase-ic-xau-phenomenon-atlas","--status",status,"--summary",summary]
    for p in artifacts:
        if Path(p).exists():cmd += ["--artifact",str(p)]
    return subprocess.run(cmd,text=True,capture_output=True).returncode

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--ib-dir",required=True); ap.add_argument("--output-dir",required=True); ap.add_argument("--policy",required=True); ap.add_argument("--progress-file"); ap.add_argument("--publisher"); args=ap.parse_args()
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); hb=Path(args.progress_file) if args.progress_file else None; policy=json.loads(Path(args.policy).read_text(encoding="utf-8")); integ=Path(args.ib_dir)/"phase_ib_integrity.json"; summ=Path(args.ib_dir)/"phase_ib_summary.json"; data=Path(args.ib_dir)/"xauusd_m5_2024_2025_news_clean.csv"
    try:
        if not integ.exists() or json.loads(integ.read_text(encoding="utf-8")).get("status")!="PASS": raise RuntimeError("Phase I-B local integrity PASS is required")
        if not summ.exists() or json.loads(summ.read_text(encoding="utf-8")).get("protected_2026_untouched") is not True: raise RuntimeError("Phase I-B provenance does not protect 2026")
        if not data.exists(): raise RuntimeError(f"missing I-B clean M5 dataset: {data}")
        heartbeat(hb,0,100,"load")
        df=pd.read_csv(data); required={"server_time","server_epoch","open","high","low","close","tick_volume","spread"}; miss=required-set(df.columns)
        if miss:raise RuntimeError(f"missing columns: {sorted(miss)}")
        if not df.server_time.astype(str).str.startswith(("2024.","2025.")).all():raise RuntimeError("protected/out-of-window row present")
        df=df.sort_values("server_epoch").reset_index(drop=True); df["year"]=df.server_time.str[:4].astype(int); df["quarter"]=pd.to_datetime(df.server_time,format="%Y.%m.%d %H:%M:%S").dt.quarter
        heartbeat(hb,10,100,"features"); df=build_features(df); heartbeat(hb,25,100,"labels"); df=add_labels(df,policy["horizons_bars"])
        d24=df[df.year==2024].copy(); d25=df[df.year==2025].copy(); cuts={}; states=[]
        for f in policy["continuous_features"]:
            c=fit_cutpoints(d24[f]);
            if c is None:continue
            cuts[f]=c; q24=assign_q(d24[f],c); q25=assign_q(d25[f],c)
            d24[f+"__q"]=q24; d25[f+"__q"]=q25
            for q in range(5):
                states.append((f"{f}:Q{q+1}","feature_quintile",f,q,None))
                for hb4 in range(6):states.append((f"{f}:Q{q+1}:H{hb4}","feature_quintile_x_server_4h_block",f,q,hb4))
        total=max(1,len(states)*len(policy["horizons_bars"])*len(policy["outcomes"])); done=0; rows=[]
        for state_name,state_family,f,q,hb4 in states:
            m24=(d24[f+"__q"].to_numpy()==q); m25=(d25[f+"__q"].to_numpy()==q)
            if hb4 is not None: m24 &= d24.hour_block.to_numpy()==hb4; m25 &= d25.hour_block.to_numpy()==hb4
            for h in policy["horizons_bars"]:
                mapping={"mean_fwd_ret_atr":f"fwd_ret_atr_h{h}","move_ge_1atr":f"move_ge_1atr_h{h}","up_first_1atr":f"up_first_1atr_h{h}"}
                for outcome,col in mapping.items():
                    r=continuous_test(d24[col].to_numpy(float),m24) if outcome=="mean_fwd_ret_atr" else binary_test(d24[col].to_numpy(float),m24); done+=1
                    if r:
                        r.update({"state":state_name,"state_family":state_family,"feature":f,"quintile":q+1,"hour_block":hb4,"horizon_bars":h,"outcome":outcome,"confirmation_mask":m25})
                        rows.append(r)
                    if done%250==0: heartbeat(hb,25+int(45*done/total),100,"discovery_tests")
        grouped={}
        for r in rows: grouped.setdefault((r["outcome"],r["horizon_bars"]),[]).append(r)
        shortlist=[]
        for grp in grouped.values():
            elig=[r for r in grp if r["n_state"]>=policy["min_state_n_discovery"] and abs(r["effect"])>=policy["minimum_absolute_effect"][r["outcome"]]]; bh_adjust(elig)
            for r in elig:
                if r["q"] is not None and r["q"]<=policy["discovery_bh_q"]:shortlist.append(r)
        heartbeat(hb,75,100,"confirmation")
        conf_groups={}
        for r in shortlist:
            h=r["horizon_bars"]; outcome=r["outcome"]; col={"mean_fwd_ret_atr":f"fwd_ret_atr_h{h}","move_ge_1atr":f"move_ge_1atr_h{h}","up_first_1atr":f"up_first_1atr_h{h}"}[outcome]; m25=r.pop("confirmation_mask")
            cr=continuous_test(d25[col].to_numpy(float),m25) if outcome=="mean_fwd_ret_atr" else binary_test(d25[col].to_numpy(float),m25)
            if cr:
                r.update({"confirmation_n_state":cr["n_state"],"confirmation_n_comp":cr["n_comp"],"confirmation_effect":cr["effect"],"confirmation_p":cr["p"]}); conf_groups.setdefault((outcome,h),[]).append(r)
        for grp in conf_groups.values():
            tmp=[]
            for r in grp: tmp.append({"p":r["confirmation_p"],"ref":r})
            bh_adjust(tmp)
            for x in tmp:x["ref"]["confirmation_q"]=x["q"]
        survivors=[]
        for r in shortlist:
            if "confirmation_effect" not in r:continue
            sign=1 if r["effect"]>0 else -1; csign=1 if r["confirmation_effect"]>0 else (-1 if r["confirmation_effect"]<0 else 0)
            if r["confirmation_n_state"]<policy["min_state_n_confirmation"] or csign!=sign:continue
            if abs(r["confirmation_effect"])<policy["confirmation_effect_retention_fraction"]*abs(r["effect"]):continue
            if r.get("confirmation_q") is None or r["confirmation_q"]>policy["confirmation_bh_q"]:continue
            h=r["horizon_bars"]; outcome=r["outcome"]; col={"mean_fwd_ret_atr":f"fwd_ret_atr_h{h}","move_ge_1atr":f"move_ge_1atr_h{h}","up_first_1atr":f"up_first_1atr_h{h}"}[outcome]; f=r["feature"]; q=r["quintile"]-1; m25=(d25[f+"__q"].to_numpy()==q)
            if r["hour_block"] is not None:m25 &= d25.hour_block.to_numpy()==r["hour_block"]
            good,qd=quarterly_signs(d25,m25,col,outcome,sign,policy["min_state_n_quarter"]); r["confirmation_quarters_same_sign"]=good; r["quarter_details"]=qd
            if good>=policy["quarters_same_sign_required"]:survivors.append(r)
        heartbeat(hb,92,100,"write")
        clean=lambda r:{k:v for k,v in r.items() if k!="confirmation_mask" and not isinstance(v,np.ndarray)}
        shortlist_clean=[clean(r) for r in shortlist]; survivors_clean=[clean(r) for r in survivors]
        pd.DataFrame(shortlist_clean).to_csv(out/"phase_ic_discovery_shortlist.csv",index=False); pd.DataFrame(survivors_clean).to_csv(out/"phase_ic_survivors.csv",index=False)
        atomic_json(out/"phase_ic_frozen_2024_cutpoints.json",cuts)
        counts={}
        for r in survivors_clean: counts[f"{r['outcome']}_h{r['horizon_bars']}"]=counts.get(f"{r['outcome']}_h{r['horizon_bars']}",0)+1
        summary={"schema":1,"phase":"I-C","technical_status":"PASS","scientific_status":"SURVIVORS_FOUND" if survivors_clean else "ZERO_SURVIVORS","generated_at_utc":datetime.now(timezone.utc).isoformat(),"rows_2024":len(d24),"rows_2025":len(d25),"features_frozen":len(cuts),"states_tested":len(states),"hypotheses_evaluated":len(rows),"discovery_shortlist":len(shortlist_clean),"confirmation_survivors":len(survivors_clean),"survivors_by_outcome_horizon":counts,"policy":policy,"protected_2026_untouched":True,"propfirm_tradability_authorized":False,"next_rule":"A Phase I-C survivor is a phenomenon candidate only. The supervisor must preregister robustness/translation before any strategy/PnL test."}
        atomic_json(out/"phase_ic_summary.json",summary); heartbeat(hb,100,100,"complete")
        artifacts=[out/"phase_ic_summary.json",out/"phase_ic_frozen_2024_cutpoints.json",out/"phase_ic_discovery_shortlist.csv",out/"phase_ic_survivors.csv",Path(args.policy)]
        rc=publish(Path(args.publisher) if args.publisher else None,"PASS",f"Phase I-C technical PASS; scientific={summary['scientific_status']}; discovery_shortlist={len(shortlist_clean)}; survivors={len(survivors_clean)}; 2026 untouched.",artifacts)
        if rc:raise RuntimeError(f"publication failed rc={rc}")
        print(json.dumps(summary,indent=2,sort_keys=True)); return 0
    except Exception as e:
        fail={"schema":1,"phase":"I-C","technical_status":"FAIL","error":repr(e),"traceback":traceback.format_exc(),"protected_2026_untouched":True}; atomic_json(out/"phase_ic_failure.json",fail); heartbeat(hb,100,100,"failed"); publish(Path(args.publisher) if args.publisher else None,"FAIL",f"Phase I-C failed: {e}",[out/"phase_ic_failure.json",Path(args.policy)]); print(json.dumps(fail,indent=2)); return 1

if __name__=="__main__": raise SystemExit(main())
