#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import pre_oos_economic_feasibility_v1_00 as econ
from pre_oos_r4_features_v1_00 import features, apply_rule, base_mask

VERSION = "r4_causal_capture_forensic_audit_v1_00"
BOUNDARY = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
YEAR_BOUNDS = {
    2024: (int(pd.Timestamp("2024-01-01", tz="UTC").timestamp()), int(pd.Timestamp("2025-01-01", tz="UTC").timestamp())),
    2025: (int(pd.Timestamp("2025-01-01", tz="UTC").timestamp()), int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())),
}
TOL = 1e-9
MARKET_META = {
    r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m1_2024_2025_raw.csv": ("M1", "raw"),
    r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m1_2024_2025_news_clean.csv": ("M1", "news-clean"),
    r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m5_2024_2025_raw.csv": ("M5", "raw"),
    r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1\xauusd_m5_2024_2025_news_clean.csv": ("M5", "news-clean"),
}


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def family(name):
    for p in ("ret", "sma", "rsi"):
        if name.startswith(p):
            return p
    return "body" if name == "body" else "other"


def describe(a):
    a = np.asarray(a, float)
    if not len(a):
        return {"count": 0, "sum": 0.0, "mean": None, "median": None, "p10": None, "p25": None, "p75": None, "p90": None, "p95": None, "p99": None, "adverse_share": None, "favorable_share": None}
    q = lambda x: float(np.percentile(a, x))
    return {
        "count": int(len(a)), "sum": float(math.fsum(a.tolist())), "mean": float(np.mean(a)), "median": float(np.median(a)),
        "p10": q(10), "p25": q(25), "p75": q(75), "p90": q(90), "p95": q(95), "p99": q(99),
        "adverse_share": float(np.mean(a < 0)), "favorable_share": float(np.mean(a > 0)),
    }


def ref_indices(raw_epochs, targets):
    idx = np.searchsorted(raw_epochs, targets)
    return idx, idx < len(raw_epochs)


def member(sorted_epochs, vals):
    idx = np.searchsorted(sorted_epochs, vals)
    safe = np.minimum(idx, len(sorted_epochs)-1)
    return (idx < len(sorted_epochs)) & (sorted_epochs[safe] == vals)


def audit_m5(m5, m1, label):
    mt, rt = econ.epochs(m5), econ.epochs(m1)
    idxs, oks = [], []
    for off in (0, 60, 120, 180, 240):
        target = mt + off
        idx = np.searchsorted(rt, target)
        safe = np.minimum(idx, len(rt)-1)
        ok = (idx < len(rt)) & (rt[safe] == target)
        idxs.append(safe); oks.append(ok)
    complete = np.logical_and.reduce(oks)
    pos = np.where(complete)[0]
    if not len(pos):
        return {"label": label, "rows": int(len(m5)), "complete_buckets": 0, "incomplete_buckets": int((~complete).sum()), "mismatch_buckets": 0, "status": "DATA_MAPPING_BLOCKED"}
    i0, i1, i2, i3, i4 = [x[pos] for x in idxs]
    expected = {
        "open": m1.open.to_numpy(float)[i0],
        "high": np.maximum.reduce([m1.high.to_numpy(float)[i0], m1.high.to_numpy(float)[i1], m1.high.to_numpy(float)[i2], m1.high.to_numpy(float)[i3], m1.high.to_numpy(float)[i4]]),
        "low": np.minimum.reduce([m1.low.to_numpy(float)[i0], m1.low.to_numpy(float)[i1], m1.low.to_numpy(float)[i2], m1.low.to_numpy(float)[i3], m1.low.to_numpy(float)[i4]]),
        "close": m1.close.to_numpy(float)[i4],
    }
    diffs, bad = {}, {}
    for c in ("open", "high", "low", "close"):
        diffs[c] = np.abs(m5[c].to_numpy(float)[pos] - expected[c])
        bad[c] = diffs[c] > TOL
    any_bad = np.logical_or.reduce(list(bad.values()))
    top = []
    score = np.maximum.reduce(list(diffs.values()))
    for local in np.argsort(score)[::-1][:20]:
        if score[local] <= 0:
            continue
        p = pos[local]
        top.append({"server_time": str(m5.time.iloc[p]), **{f"{c}_abs_diff": float(diffs[c][local]) for c in diffs}})
    return {
        "label": label, "rows": int(len(m5)), "complete_buckets": int(len(pos)), "incomplete_buckets": int((~complete).sum()),
        "mismatch_buckets": int(any_bad.sum()), "field_mismatch_counts": {c: int(bad[c].sum()) for c in bad},
        "max_abs_diff": {c: float(diffs[c].max()) for c in diffs}, "top_mismatches": top,
        "status": "PASS" if not any_bad.any() else "DATA_MAPPING_BLOCKED",
    }


def clean_subset(raw, clean):
    rt, ct = econ.epochs(raw), econ.epochs(clean)
    idx = np.searchsorted(rt, ct); safe = np.minimum(idx, len(rt)-1)
    ok = (idx < len(rt)) & (rt[safe] == ct)
    mismatch = np.zeros(len(clean), bool)
    maxdiff = {}
    for c in ("open", "high", "low", "close"):
        diff = np.full(len(clean), np.nan)
        good = np.where(ok)[0]
        diff[good] = np.abs(clean[c].to_numpy(float)[good] - raw[c].to_numpy(float)[safe[good]])
        mismatch |= np.isfinite(diff) & (diff > TOL)
        maxdiff[c] = float(np.nanmax(diff)) if np.isfinite(diff).any() else None
    return {"missing_in_raw": int((~ok).sum()), "ohlc_mismatch_rows": int(mismatch.sum()), "max_abs_diff": maxdiff, "status": "PASS" if ok.all() and not mismatch.any() else "DATA_MAPPING_BLOCKED"}


def load_inputs():
    allowed = {**econ.MARKETS, econ.SOURCE: econ.SOURCE_HASH}
    accesses = []
    source = json.loads(econ.verified_bytes(econ.SOURCE, allowed, accesses))
    if source.get("survivor_count") != 500 or len(source.get("survivors", [])) != 500:
        raise econ.BlockedData("expected exactly 500 R4 survivors")
    frames = {}
    for p, (tf, _) in MARKET_META.items():
        if p not in econ.MARKETS:
            raise econ.BlockedData("market pin mismatch")
        frames[p] = econ.parse_market(econ.verified_bytes(p, allowed, accesses), tf)
    return source, frames, accesses


def immediate(df, raw, signals, rule, tf, year):
    st, rt = econ.epochs(df), econ.epochs(raw)
    close = df.close.to_numpy(float)
    target = st + tf
    idx, ok = ref_indices(rt, target)
    lo, hi = YEAR_BOUNDS[year]
    ok &= (target >= lo) & (target < hi)
    vals = np.full(len(df), np.nan)
    rows = np.where(ok)[0]
    vals[rows] = rule["direction"] * (raw.open.to_numpy(float)[idx[rows]] - close[rows])
    base = base_mask(df, rule)
    a = vals[signals & base & np.isfinite(vals)]
    b = vals[(~signals) & base & np.isfinite(vals)]
    return {
        "selected_count": int(len(a)), "complement_count": int(len(b)),
        "selected_mean": float(np.mean(a)) if len(a) else None,
        "complement_mean": float(np.mean(b)) if len(b) else None,
        "selected_minus_complement": float(np.mean(a)-np.mean(b)) if len(a) and len(b) else None,
    }


def self_test():
    d, cs, ce, oe, ox = -1, 100., 95., 101., 96.
    b = d*(ce-cs); ent = d*(cs-oe); ex = d*(ox-ce); c = d*(ox-oe)
    if not math.isclose(c, b+ent+ex, abs_tol=1e-12):
        raise RuntimeError("decomposition self-test failed")


def run(args):
    self_test()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=False)
    progress = Path(args.progress_file); progress.parent.mkdir(parents=True, exist_ok=True)
    source, frames, accesses = load_inputs()
    p_m1r = next(p for p, m in MARKET_META.items() if m == ("M1", "raw"))
    p_m1c = next(p for p, m in MARKET_META.items() if m == ("M1", "news-clean"))
    p_m5r = next(p for p, m in MARKET_META.items() if m == ("M5", "raw"))
    p_m5c = next(p for p, m in MARKET_META.items() if m == ("M5", "news-clean"))
    m1r, m1c, m5r, m5c = frames[p_m1r], frames[p_m1c], frames[p_m5r], frames[p_m5c]
    mapping = {
        "m5_raw_vs_m1_raw": audit_m5(m5r, m1r, "m5_raw_vs_m1_raw"),
        "m5_clean_vs_m1_raw": audit_m5(m5c, m1r, "m5_clean_vs_m1_raw"),
        "m5_clean_subset_of_m5_raw": clean_subset(m5r, m5c),
    }
    mapping_pass = all(v["status"] == "PASS" for v in mapping.values())
    cache = {p: features(df) for p, df in frames.items()}
    rt = econ.epochs(m1r); ro = m1r.open.to_numpy(float); clean_t = econ.epochs(m1c)

    ev = {k: [] for k in ("entry","exit","year","tf","kind","h","dir","fam")}
    rows = []; totals = {2024: defaultdict(float), 2025: defaultdict(float)}; news = defaultdict(float)

    for n, rule in enumerate(source["survivors"]):
        cid = f"R4P-{n+1:04d}"; path = rule["dataset"]
        if path not in frames: raise econ.BlockedData("candidate dataset not pinned")
        tf_name, kind = MARKET_META[path]; tf = 60 if tf_name == "M1" else 300; fam = family(rule["feature"])
        df = frames[path]; ft, atr = cache[path]; sig = apply_rule(df, ft, rule); idx_all = np.where(sig)[0]
        st = econ.epochs(df); cl = df.close.to_numpy(float); av = atr.to_numpy(float); h = int(rule["horizon_bars"]); direction = int(rule["direction"])
        row = {"id":cid,"timeframe":tf_name,"kind":kind,"feature":rule["feature"],"family":fam,"horizon":h,"direction":direction,"signals_total":int(sig.sum()),
               "signature_sha256":sha(canon({k:rule[k] for k in econ.SIGNATURE_FIELDS}))}
        for year in (2024,2025):
            u = idx_all[idx_all+h < len(df)]
            if len(u):
                j = u+h; et = st[u]+tf; xt = st[j]+tf; lo,hi = YEAR_BOUNDS[year]; keep=(et>=lo)&(et<hi)&(xt>=lo)&(xt<hi); u=u[keep]; j=j[keep]; et=et[keep]; xt=xt[keep]
            if len(u):
                ei,eok=ref_indices(rt,et); xi,xok=ref_indices(rt,xt); good=eok&xok; u=u[good]; j=j[good]; ei=ei[good]; xi=xi[good]
            if len(u):
                b=direction*(cl[j]-cl[u]); ent=direction*(cl[u]-ro[ei]); ex=direction*(ro[xi]-cl[j]); c=direction*(ro[xi]-ro[ei]); err=np.max(np.abs(c-(b+ent+ex)))
                if err>1e-10: raise RuntimeError(f"identity failed {cid} {err}")
                goodatr=np.isfinite(av[u])&(av[u]>0); a=direction*(cl[j][goodatr]-cl[u][goodatr])/av[u][goodatr]
            else:
                b=ent=ex=c=a=np.array([],float); err=0.0
            row.update({f"events_{year}":int(len(b)),f"A_mean_atr_{year}":float(np.mean(a)) if len(a) else None,f"B_gross_{year}":float(math.fsum(b.tolist())),
                        f"entry_delta_{year}":float(math.fsum(ent.tolist())),f"exit_delta_{year}":float(math.fsum(ex.tolist())),f"C_gross_{year}":float(math.fsum(c.tolist())),f"identity_error_{year}":float(err)})
            for k,v in (("B",row[f"B_gross_{year}"]),("ENTRY",row[f"entry_delta_{year}"]),("EXIT",row[f"exit_delta_{year}"]),("C",row[f"C_gross_{year}"])): totals[year][k]+=v
            totals[year]["events"] += len(b)
            if len(ent):
                ev["entry"].append(ent); ev["exit"].append(ex); ev["year"].append(np.full(len(ent),year,np.int16)); ev["tf"].append(np.full(len(ent),1 if tf_name=="M1" else 5,np.int8)); ev["kind"].append(np.full(len(ent),0 if kind=="raw" else 1,np.int8)); ev["h"].append(np.full(len(ent),h,np.int16)); ev["dir"].append(np.full(len(ent),direction,np.int8)); ev["fam"].append(np.full(len(ent),{"ret":1,"sma":2,"rsi":3,"body":4}.get(fam,9),np.int8))
            imm=immediate(df,m1r,sig,rule,tf,year)
            for k,v in imm.items(): row[f"immediate_{year}_{k}"]=v

        ledger, counts = econ.replay(df,m1r,sig,h,direction,tf,None,None); econ.validate_ledger(ledger,counts)
        row["ignored_overlap_signals"]=int(counts["ignored_overlap_signals"]); row["executable_trades_all"]=int(counts["executable_trades"]); row["overlap_rate"]=float(counts["ignored_overlap_signals"]/counts["signals_total"]) if counts["signals_total"] else 0.0
        for year in (2024,2025):
            yr=[r for r in ledger if str(year) in r["periods"]]; e1=econ.stats(yr,"E1"); stx=econ.stats(yr,"STRESS"); d=float(e1["gross"]); cost=float(e1["spread"]+e1["slippage"]+e1["commission"])
            row.update({f"D_gross_{year}":d,f"overlap_delta_{year}":d-row[f"C_gross_{year}"],f"E1_cost_{year}":cost,f"E1_net_{year}":float(e1["net"]),f"STRESS_net_{year}":float(stx["net"]),f"E1_cost_per_trade_{year}":cost/e1["trades"] if e1["trades"] else None})
            totals[year]["D"]+=d; totals[year]["OVERLAP"]+=row[f"overlap_delta_{year}"]; totals[year]["E1_COST"]+=cost; totals[year]["E1_NET"]+=row[f"E1_net_{year}"]; totals[year]["TRADES"]+=e1["trades"]
        if kind=="news-clean" and ledger:
            en=np.array([r["entry"] for r in ledger],np.int64); exx=np.array([r["exit"] for r in ledger],np.int64); ein=member(clean_t,en); xin=member(clean_t,exx); bad=(~ein)|(~xin); badidx=np.where(bad)[0]
            row.update({"news_entry_absent":int((~ein).sum()),"news_exit_absent":int((~xin).sum()),"news_any_absent":int(bad.sum()),"news_any_absent_share":float(bad.mean()),
                        "news_anomaly_gross":float(math.fsum(ledger[i]["profiles"]["E1"]["gross"] for i in badidx)),"news_anomaly_E1_net":float(math.fsum(ledger[i]["profiles"]["E1"]["net"] for i in badidx))})
            news["trades"]+=len(ledger); news["entry"]+=row["news_entry_absent"]; news["exit"]+=row["news_exit_absent"]; news["any"]+=row["news_any_absent"]; news["gross"]+=row["news_anomaly_gross"]; news["net"]+=row["news_anomaly_E1_net"]
        else:
            row.update({"news_entry_absent":0,"news_exit_absent":0,"news_any_absent":0,"news_any_absent_share":0.0,"news_anomaly_gross":0.0,"news_anomaly_E1_net":0.0})
        rows.append(row)
        econ.atomic_json(progress,{"stage":"forensic_candidate_replay","completed":n+1,"total":500,"candidate":cid,"mapping_status":"PASS" if mapping_pass else "DATA_MAPPING_BLOCKED","updated_at_utc":pd.Timestamp.now(tz="UTC").isoformat()})

    arr={k:(np.concatenate(v) if v else np.array([])) for k,v in ev.items()}
    attribution={"overall":{"entry":describe(arr["entry"]),"exit":describe(arr["exit"])},"groups":{}}
    dims={"year":(arr["year"],{2024:"2024",2025:"2025"}),"timeframe":(arr["tf"],{1:"M1",5:"M5"}),"kind":(arr["kind"],{0:"raw",1:"news-clean"}),"horizon":(arr["h"],{1:"1",3:"3",6:"6",12:"12",24:"24",48:"48"}),"direction":(arr["dir"],{1:"long",-1:"short"}),"family":(arr["fam"],{1:"ret",2:"sma",3:"rsi",4:"body",9:"other"})}
    for name,(codes,labels) in dims.items():
        attribution["groups"][name]={label:{"entry":describe(arr["entry"][codes==code]),"exit":describe(arr["exit"][codes==code])} for code,label in labels.items()}

    positive={}; decomp={}; imm={}
    for year in (2024,2025):
        positive[str(year)]={"B_positive":sum(r[f"B_gross_{year}"]>0 for r in rows),"C_positive":sum(r[f"C_gross_{year}"]>0 for r in rows),"D_positive":sum(r[f"D_gross_{year}"]>0 for r in rows),"E1_net_positive":sum(r[f"E1_net_{year}"]>0 for r in rows)}
        g=totals[year]; change=g["C"]-g["B"]; adverse=max(-g["ENTRY"],0)+max(-g["EXIT"],0)
        decomp[str(year)]={"events":int(g["events"]),"B_close_gross":float(g["B"]),"entry_delta":float(g["ENTRY"]),"exit_delta":float(g["EXIT"]),"C_nextopen_no_overlap_gross":float(g["C"]),"identity_error":float(g["C"]-(g["B"]+g["ENTRY"]+g["EXIT"])),"B_to_C_change":float(change),
                           "entry_signed_share":float(g["ENTRY"]/change) if change else None,"exit_signed_share":float(g["EXIT"]/change) if change else None,"entry_share_adverse_components":float(max(-g["ENTRY"],0)/adverse) if adverse else None,"exit_share_adverse_components":float(max(-g["EXIT"],0)/adverse) if adverse else None,
                           "D_overlap_gross":float(g["D"]),"OVERLAP_DELTA":float(g["OVERLAP"]),"E1_cost":float(g["E1_COST"]),"E1_net":float(g["E1_NET"]),"E1_average_cost_per_trade":float(g["E1_COST"]/g["TRADES"]) if g["TRADES"] else None}
        diffs=[r[f"immediate_{year}_selected_minus_complement"] for r in rows if r[f"immediate_{year}_selected_minus_complement"] is not None]
        imm[str(year)]={"candidate_count":len(diffs),"candidate_mean_difference":float(np.mean(diffs)) if diffs else None,"candidate_median_difference":float(np.median(diffs)) if diffs else None,"selected_worse_count":int(sum(x<0 for x in diffs)),"selected_better_count":int(sum(x>0 for x in diffs))}

    news_summary={"trades":int(news["trades"]),"entry_absent":int(news["entry"]),"exit_absent":int(news["exit"]),"any_absent":int(news["any"]),"any_absent_share":float(news["any"]/news["trades"]) if news["trades"] else None,"anomaly_gross":float(news["gross"]),"anomaly_E1_net":float(news["net"])}
    status="PASS_INTERPRETABLE" if mapping_pass else "DATA_MAPPING_BLOCKED"

    csvp=out/"candidate_forensic_summary.csv"; fields=sorted({k for r in rows for k in r})
    with csvp.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    result={"schema":1,"audit":VERSION,"status":status,"population_count":len(rows),"protected_2026_opened":False,"mapping":mapping,"positive_counts":positive,"decomposition":decomp,"attribution":attribution,"immediate_post_close_selected_vs_complement":imm,"news_clean_execution_audit":news_summary,
            "candidate_rows_sha256":sha(canon(rows)),"provenance":{"source":econ.SOURCE,"source_sha256":econ.SOURCE_HASH,"market_hashes":econ.MARKETS,"input_accesses":accesses,"script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"generated_at_utc":pd.Timestamp.now(tz="UTC").isoformat()},
            "interpretation":"Descriptive forensic audit only; no discovery, retuning, candidate selection, protected OOS, live deployment or downstream authorization."}
    rp=out/"r4_causal_capture_forensic_result.json"; econ.atomic_json(rp,result)
    md=["# R4 causal-capture forensic audit","",f"Verdict: **{status}**","",f"M5 raw -> M1 raw: **{mapping['m5_raw_vs_m1_raw']['status']}**",f"M5 clean -> M1 raw: **{mapping['m5_clean_vs_m1_raw']['status']}**",f"M5 clean subset raw: **{mapping['m5_clean_subset_of_m5_raw']['status']}**",""]
    for y in ("2024","2025"):
        p=positive[y]; d=decomp[y]; md += [f"## {y}","",f"B positive {p['B_positive']}/500; C positive {p['C_positive']}/500; D positive {p['D_positive']}/500; E1 net positive {p['E1_net_positive']}/500.",f"B={d['B_close_gross']:.6f}; ENTRY={d['entry_delta']:.6f}; EXIT={d['exit_delta']:.6f}; C={d['C_nextopen_no_overlap_gross']:.6f}; OVERLAP={d['OVERLAP_DELTA']:.6f}; E1 cost={d['E1_cost']:.6f}; E1 net={d['E1_net']:.6f}.",""]
    md += ["## News-clean execution references","",f"Any raw-M1 reference absent from M1 clean: {news_summary['any_absent']} / {news_summary['trades']} trades.","","No new research phase is authorized by this audit."]
    mdp=out/"SUMMARY.md"; mdp.write_text("\n".join(md)+"\n",encoding="utf-8")
    econ.atomic_json(progress,{"stage":"complete","completed":500,"total":500,"status":status,"mapping_status":"PASS" if mapping_pass else "DATA_MAPPING_BLOCKED","positive_counts":positive,"updated_at_utc":pd.Timestamp.now(tz="UTC").isoformat()})
    if args.publisher:
        ps="PASS" if mapping_pass else "FAIL"; summary=f"{status}; immutable 500-candidate causal-capture forensic audit; no discovery/no 2026/no downstream authorization."
        subprocess.run(["python",args.publisher,"--phase","r4-causal-capture-forensic-audit","--status",ps,"--summary",summary,"--artifact",str(rp),"--artifact",str(csvp),"--artifact",str(mdp)],check=True)
    print(json.dumps({"status":status,"mapping":"PASS" if mapping_pass else "DATA_MAPPING_BLOCKED","positive_counts":positive,"news_clean_any_reference_absent":news_summary["any_absent"]},sort_keys=True))
    return 0


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir",required=True); ap.add_argument("--progress-file",required=True); ap.add_argument("--publisher"); return run(ap.parse_args())

if __name__=="__main__": raise SystemExit(main())
