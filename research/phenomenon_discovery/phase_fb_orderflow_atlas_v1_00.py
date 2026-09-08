#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, math, random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FEATURES = [
    "spot_taker_imbalance","perp_taker_imbalance","taker_imbalance_diff",
    "perp_spot_basis_bps","log_quote_volume_ratio","log_trade_count_ratio",
    "spot_taker_imbalance_change_15m","spot_taker_imbalance_change_1h",
    "perp_taker_imbalance_change_15m","perp_taker_imbalance_change_1h",
    "taker_imbalance_diff_change_15m","taker_imbalance_diff_change_1h",
    "perp_spot_basis_bps_change_15m","perp_spot_basis_bps_change_1h",
    "log_quote_volume_ratio_change_15m","log_quote_volume_ratio_change_1h",
    "log_trade_count_ratio_change_15m","log_trade_count_ratio_change_1h",
]
QPROBS=(0.2,0.4,0.6,0.8)
MIN_DISCOVERY_ANNUAL_N=500
MIN_DISCOVERY_HALF_N=180
MIN_CONFIRM_ANNUAL_N=300
MIN_CONFIRM_QUARTER_N=50
MIN_QUARTER_ELIGIBLE=6
MIN_QUARTER_MATCH_RATE=0.75
RETENTION_FRACTION=0.25
TOP_PER_OUTCOME=25
BOOTSTRAPS=3000
BLOCK_DAYS=5
BH_Q_MAX=0.10


def finite(x):
    if x in (None,""): return None
    try: v=float(x)
    except (TypeError,ValueError): return None
    return v if math.isfinite(v) else None

def quantiles(vals):
    s=sorted(vals); n=len(s); out=[]
    for p in QPROBS:
        pos=p*(n-1); lo=int(math.floor(pos)); hi=int(math.ceil(pos)); w=pos-lo
        out.append(s[lo] if lo==hi else s[lo]*(1-w)+s[hi]*w)
    return out

def qbin(v,cuts):
    b=1
    for c in cuts:
        if v>c: b+=1
        else: break
    return b

def ret_1h_atr(r):
    ret,close,atr=finite(r.get("future_return_1h_pct")),finite(r.get("close")),finite(r.get("atr14"))
    if ret is None or close is None or atr is None or atr<=0: return None
    return (ret/100.0)*close/atr

def up_first(r):
    t=r.get("future_first_touch_1atr_1h","")
    return 1.0 if t=="UP" else 0.0 if t=="DOWN" else None
OUTCOMES={"direction_1h_atr":ret_1h_atr,"up_first_1atr_1h":up_first}

def load_joined(flow_path, feat_path, year):
    feat={}
    with feat_path.open("r",newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("timestamp_utc","").startswith(f"{year}-"): feat[int(r["timestamp_ms"])]=r
    rows=[]
    with flow_path.open("r",newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("timestamp_utc","").startswith(f"{year}-"): continue
            ts=int(r["timestamp_ms"]); fr=feat.get(ts)
            if fr is None: continue
            raw=dict(fr); raw.update(r)
            dt=datetime.fromisoformat(r["timestamp_utc"])
            rows.append({"raw":raw,"half":1 if dt.month<=6 else 2,"quarter":((dt.month-1)//3)+1,"day":dt.date().isoformat()})
    return rows

def learn_cuts(rows):
    out={}
    for f in FEATURES:
        vals=[v for x in rows if (v:=finite(x["raw"].get(f))) is not None]
        if len(vals)<1000: raise RuntimeError(f"too few values for {f}: {len(vals)}")
        out[f]=quantiles(vals)
    return out

def add_bins(rows,cuts):
    for x in rows:
        x["bins"]={f:qbin(v,cuts[f]) for f in FEATURES if (v:=finite(x["raw"].get(f))) is not None}
        x["outcomes"]={n:fn(x["raw"]) for n,fn in OUTCOMES.items()}

def members(rows,feature,q): return {i for i,x in enumerate(rows) if x["bins"].get(feature)==q}
def baseline(rows,outcome,subset=None):
    vals=[x["outcomes"][outcome] for i,x in enumerate(rows) if (subset is None or subset(i,x)) and x["outcomes"][outcome] is not None]
    return sum(vals)/len(vals) if vals else None

def effect(rows,mem,outcome,subset=None):
    b=baseline(rows,outcome,subset); vals=[]
    for i in mem:
        x=rows[i]
        if subset is not None and not subset(i,x): continue
        v=x["outcomes"][outcome]
        if v is not None: vals.append(v)
    return (len(vals), None if b is None or not vals else sum(vals)/len(vals)-b)
def sgn(x): return 1 if x>0 else -1 if x<0 else 0

def stable_seed(*parts): return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:16],16)
def block_p(rows,mem,outcome,obs,wanted,seed):
    valid=[x for x in rows if x["outcomes"][outcome] is not None]
    base=sum(x["outcomes"][outcome] for x in valid)/len(valid)
    days=sorted({x["day"] for x in valid}); pos={d:i for i,d in enumerate(days)}
    ds=[0.0]*len(days); dn=[0]*len(days)
    for i in mem:
        x=rows[i]; v=x["outcomes"][outcome]
        if v is None: continue
        j=pos[x["day"]]; ds[j]+=v; dn[j]+=1
    centered=[ds[i]-dn[i]*base-obs*dn[i] for i in range(len(days))]
    bn=[]; bd=[]
    for start in range(len(days)):
        num=0.0; den=0
        for k in range(BLOCK_DAYS):
            j=(start+k)%len(days); num+=centered[j]; den+=dn[j]
        bn.append(num); bd.append(den)
    rng=random.Random(seed); need=int(math.ceil(len(days)/BLOCK_DAYS)); extreme=0; validn=0
    for _ in range(BOOTSTRAPS):
        num=0.0; den=0
        for _b in range(need):
            j=rng.randrange(len(days)); num+=bn[j]; den+=bd[j]
        if den<=0: continue
        e=num/den; validn+=1; extreme+=int(e>=obs) if wanted>0 else int(e<=obs)
    return (extreme+1)/(validn+1)
def bh(items):
    ordered=sorted(items,key=lambda x:x[1]); m=len(ordered); out={}; run=1.0
    for rev in range(m-1,-1,-1):
        idx,p=ordered[rev]; rank=rev+1; q=min(1.0,p*m/rank); run=min(run,q); out[idx]=run
    return out

def write_csv(path,rows):
    if not rows: path.write_text("state\n",encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--flow-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1"); ap.add_argument("--features-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1"); ap.add_argument("--output-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_fb_v1"); a=ap.parse_args()
    flow,feat,out=Path(a.flow_dir),Path(a.features_dir),Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    r24={}; r25={}; cuts={}
    for sym in ("BTCUSDT","ETHUSDT"):
        ff=flow/f"{sym}_binance_spot_um_5m_orderflow_2024-01-01_2026-01-01.csv"
        ffs=sorted(feat.glob(f"{sym}_bybit_5m_oi_price_*_features_v1.csv"))
        if not ff.exists() or len(ffs)!=1: raise RuntimeError(f"missing inputs for {sym}")
        r24[sym]=load_joined(ff,ffs[0],2024); r25[sym]=load_joined(ff,ffs[0],2025); cuts[sym]=learn_cuts(r24[sym]); add_bins(r24[sym],cuts[sym]); add_bins(r25[sym],cuts[sym]); print(f"{sym}: 2024={len(r24[sym])} 2025={len(r25[sym])}")
    universe=[]; eligible=defaultdict(list)
    for feature in FEATURES:
        for q in range(1,6):
            state=f"{feature}=Q{q}"
            for outcome in OUTCOMES:
                rec={"state":state,"outcome":outcome,"feature":feature,"q":q}; effects=[]; wanted=None; ok=True; halfok=True
                for sym in ("BTCUSDT","ETHUSDT"):
                    mem=members(r24[sym],feature,q); n,e=effect(r24[sym],mem,outcome); rec[f"{sym.lower()}_2024_n"]=n; rec[f"{sym.lower()}_2024_effect"]=e
                    if n<MIN_DISCOVERY_ANNUAL_N or e is None or sgn(e)==0: ok=False
                    else:
                        effects.append(abs(e)); wanted=sgn(e) if wanted is None else wanted; ok=ok and sgn(e)==wanted
                    for h in (1,2):
                        hn,he=effect(r24[sym],mem,outcome,lambda _i,x,h=h:x["half"]==h); rec[f"{sym.lower()}_2024_h{h}_n"]=hn; rec[f"{sym.lower()}_2024_h{h}_effect"]=he
                        if hn<MIN_DISCOVERY_HALF_N or he is None or (wanted is not None and sgn(he)!=wanted): halfok=False
                rec["discovery_sign"]=wanted if ok else None; rec["discovery_worst_abs_effect"]=min(effects) if ok and len(effects)==2 else None; rec["discovery_eligible"]=bool(ok and halfok); universe.append(rec)
                if rec["discovery_eligible"]: eligible[outcome].append(rec)
    frozen=[]
    for outcome,items in eligible.items(): frozen += [dict(x) for x in sorted(items,key=lambda r:r["discovery_worst_abs_effect"],reverse=True)[:TOP_PER_OUTCOME]]
    frozen.sort(key=lambda r:(r["outcome"],-r["discovery_worst_abs_effect"],r["state"]))
    up=out/"phase_fb_2024_universe.csv"; fp=out/"phase_fb_frozen_shortlist_2024.csv"; write_csv(up,universe); write_csv(fp,frozen); frozen_hash=sha(fp)
    conf=[]
    for rec0 in frozen:
        rec=dict(rec0); wanted=int(rec["discovery_sign"]); feature=rec["feature"]; q=int(rec["q"]); outcome=rec["outcome"]; effects=[]; annual=True; qelig=qmatch=0; ps=[]
        for sym in ("BTCUSDT","ETHUSDT"):
            mem=members(r25[sym],feature,q); n,e=effect(r25[sym],mem,outcome); rec[f"{sym.lower()}_2025_n"]=n; rec[f"{sym.lower()}_2025_effect"]=e
            if n<MIN_CONFIRM_ANNUAL_N or e is None or sgn(e)!=wanted: annual=False
            else:
                effects.append(abs(e)); p=block_p(r25[sym],mem,outcome,e,wanted,stable_seed("phase-fb",rec["state"],outcome,sym)); ps.append(p); rec[f"{sym.lower()}_block_p"]=p
            for qq in range(1,5):
                qn,qe=effect(r25[sym],mem,outcome,lambda _i,x,qq=qq:x["quarter"]==qq); rec[f"{sym.lower()}_2025_q{qq}_n"]=qn; rec[f"{sym.lower()}_2025_q{qq}_effect"]=qe
                if qn>=MIN_CONFIRM_QUARTER_N and qe is not None: qelig+=1; qmatch+=int(sgn(qe)==wanted)
        rec["confirm_same_sign_both"]=annual; rec["confirm_worst_abs_effect"]=min(effects) if annual and len(effects)==2 else None; rec["confirm_retains_effect"]=bool(rec["confirm_worst_abs_effect"] is not None and rec["confirm_worst_abs_effect"]>=RETENTION_FRACTION*rec["discovery_worst_abs_effect"]); rec["quarter_eligible"]=qelig; rec["quarter_match"]=qmatch; rec["quarter_match_rate"]=qmatch/qelig if qelig else 0.0; rec["quarter_stable"]=qelig>=MIN_QUARTER_ELIGIBLE and rec["quarter_match_rate"]>=MIN_QUARTER_MATCH_RATE; rec["worst_symbol_p"]=max(ps) if len(ps)==2 else 1.0; conf.append(rec)
    qmap=bh([(i,r["worst_symbol_p"]) for i,r in enumerate(conf)])
    passes=[]
    for i,r in enumerate(conf):
        r["worst_symbol_bh_q"]=qmap[i]; r["phase_fb_screen_pass"]=bool(r["confirm_same_sign_both"] and r["confirm_retains_effect"] and r["quarter_stable"] and qmap[i]<=BH_Q_MAX)
        if r["phase_fb_screen_pass"]: passes.append(r)
    cp=out/"phase_fb_2025_confirmation.csv"; pp=out/"phase_fb_distinct_passes.csv"; write_csv(cp,conf); write_csv(pp,passes)
    summary={"schema":1,"phase":"F-B","status":"DISCOVERY_ROBUSTNESS_ONLY","features":FEATURES,"states_tested":len(FEATURES)*5,"universe_tests_total":len(FEATURES)*5*len(OUTCOMES),"frozen_shortlist_count":len(frozen),"frozen_shortlist_sha256":frozen_hash,"phase_fb_screen_pass_count":len(passes),"passes_by_outcome":{o:sum(1 for r in passes if r["outcome"]==o) for o in OUTCOMES},"protected_2026_untouched":True,"independent_validation":False,"gates":{"top_per_outcome":TOP_PER_OUTCOME,"bootstrap_paths":BOOTSTRAPS,"circular_block_days":BLOCK_DAYS,"bh_q_max":BH_Q_MAX,"confirmation_effect_retention_fraction":RETENTION_FRACTION,"quarter_match_rate_min":MIN_QUARTER_MATCH_RATE,"quarter_min_eligible_blocks":MIN_QUARTER_ELIGIBLE},"warning":"Phase F-B uses inspected 2024-2025 data. Passing states are candidates only; freeze before any 2026 validation."}
    (out/"phase_fb_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(summary,indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
