from pathlib import Path
import argparse
import json
import re
import time
import zipfile

import numpy as np
import pandas as pd

ENGINE_VERSION="V106.0"
PRIORITY=["financial_conditions","treasury_auctions","fomc_fed","alfred_vintage","cfe_volume_oi","cboe_vol"]

KEYS={
 "financial_conditions":["financial_conditions","financial conditions","nfci","stlfs","conditions"],
 "treasury_auctions":["treasury_auction","treasury auction","auction_date","bid_to_cover","bid-to-cover"],
 "fomc_fed":["fomc","federalreserve","federal_reserve","fed_minutes","fed_statement"],
 "alfred_vintage":["alfred","realtime_start","vintage"],
 "cfe_volume_oi":["cfe","open_interest","open interest","futures_volume","volume_oi"],
 "cboe_vol":["cboe","vix","vvix","vix9d","gvz","ovx"],
}

DATE_HINTS=["available_at","release","publish","publication","realtime_start","vintage","auction_date","report_date","observation_date","date","timestamp","time"]

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def classify(path,columns=None):
    s=(str(path)+" "+" ".join(map(str,columns or []))).lower()
    for fam,keys in KEYS.items():
        if any(k in s for k in keys):
            return fam
    return None

def year_tokens(path):
    return [int(x) for x in re.findall(r"(?<!\d)(20\d{2}|19\d{2})(?!\d)",str(path))]

def clearly_safe_pre2023(path):
    s=str(path).lower()
    if "pre2023" in s or "pre_2023" in s or "2009_2013" in s or "2010_2013" in s:
        return True
    ys=year_tokens(path)
    return bool(ys) and max(ys)<=2022

def schema_read(path):
    ext=path.suffix.lower()
    if ext==".parquet":
        d=pd.read_parquet(path)
    elif ext==".csv":
        d=pd.read_csv(path)
    elif ext in [".xlsx",".xls"]:
        d=pd.read_excel(path)
    else:
        return None
    return d

def best_date_columns(d):
    out=[]
    for c in d.columns:
        z=str(c).lower()
        if any(h in z for h in DATE_HINTS):
            out.append(c)
    return out

def inspect_file(path):
    row={"path":str(path),"extension":path.suffix.lower(),"safe_pre2023":clearly_safe_pre2023(path)}
    if not row["safe_pre2023"]:
        row.update({"inspection_status":"SKIPPED_UNBOUNDED_WINDOW","rows":np.nan,"columns":"","date_columns":"","min_date":None,"max_date":None,"has_available_at":False,"has_release_semantics":False})
        return row
    try:
        if path.suffix.lower()==".zip":
            with zipfile.ZipFile(path) as z:
                members=z.namelist()
            row.update({"inspection_status":"ZIP_NAMES_ONLY","rows":np.nan,"columns":"","date_columns":"","min_date":None,"max_date":None,
                        "has_available_at":False,"has_release_semantics":False,"zip_members":len(members)})
            return row
        d=schema_read(path)
        if d is None:
            row.update({"inspection_status":"UNSUPPORTED_METADATA_ONLY","rows":np.nan,"columns":"","date_columns":"","min_date":None,"max_date":None,"has_available_at":False,"has_release_semantics":False})
            return row
        cols=[str(c) for c in d.columns]
        dcols=best_date_columns(d)
        mins=[];maxs=[]
        for c in dcols:
            try:
                z=pd.to_datetime(d[c],errors="coerce")
                z=z[z.notna()]
                if len(z):
                    # Fail closed if a supposedly safe file contains post-2022 timestamps.
                    if z.max().year>=2023:
                        row.update({"inspection_status":"BLOCKED_CONTAINS_2023_PLUS","rows":len(d),"columns":"|".join(cols[:120]),"date_columns":"|".join(map(str,dcols)),
                                    "min_date":str(z.min()),"max_date":str(z.max()),"has_available_at":False,"has_release_semantics":False})
                        return row
                    mins.append(z.min());maxs.append(z.max())
            except Exception:
                pass
        low=min(mins) if mins else None; high=max(maxs) if maxs else None
        lcols=[c.lower() for c in cols]
        has_av=any("available_at" in c for c in lcols)
        has_rel=any(any(h in c for h in ["release","publish","publication","realtime_start","vintage","auction_date","available_at"]) for c in lcols)
        row.update({"inspection_status":"INSPECTED","rows":int(len(d)),"columns":"|".join(cols[:120]),"date_columns":"|".join(map(str,dcols)),
                    "min_date":str(low) if low is not None else None,"max_date":str(high) if high is not None else None,
                    "has_available_at":bool(has_av),"has_release_semantics":bool(has_rel)})
        return row
    except Exception as e:
        row.update({"inspection_status":"READ_ERROR","error":repr(e)[:500],"rows":np.nan,"columns":"","date_columns":"","min_date":None,"max_date":None,"has_available_at":False,"has_release_semantics":False})
        return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);dl=root/"DataLake"
    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v106_source_audit";base.mkdir(parents=True,exist_ok=True)
    rid="GEF106-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S");out=base/rid;out.mkdir(parents=True,exist_ok=False);t0=time.time()
    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,"percent":round(100*step/total,1),
           "elapsed_s":round(time.time()-t0,1),"message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF106] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,8,"locate frozen V85 catalog; zero edge trials")
    v85runs=[p for p in sorted((root/"Research"/"Autonomous"/"guardian_edge_factory_v85").glob("GEF85-*")) if (p/"RUN_RECEIPT.json").exists()]
    if not v85runs: raise RuntimeError("No completed V85")
    v85=v85runs[-1]
    cat=pd.read_csv(v85/"FROZEN_ELIGIBLE_FEATURES.csv")
    fc=cat.groupby(["layer","family"]).size().reset_index(name="features")
    fc.to_csv(out/"V85_FAMILY_COUNTS.csv",index=False)
    status(2,8,"V85 taxonomy frozen",families=len(fc),features=len(cat))

    exts={".csv",".parquet",".xlsx",".xls",".zip",".xml",".json"}
    candidates=[]
    for p in dl.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in exts: continue
        fam=classify(p)
        if fam:
            candidates.append((p,fam))
    status(3,8,"candidate source files located",files=len(candidates))

    rows=[]
    for i,(p,fam) in enumerate(candidates,1):
        z=inspect_file(p);z["family"]=fam;rows.append(z)
        if i==1 or i==len(candidates) or i%25==0:
            print(f"[GEF106] inspect {i}/{len(candidates)}",flush=True)
    D=pd.DataFrame(rows)
    if D.empty:
        D=pd.DataFrame(columns=["path","family","inspection_status","safe_pre2023","min_date","max_date","has_available_at","has_release_semantics"])
    D.to_csv(out/"SOURCE_FILE_AUDIT.csv",index=False)
    status(4,8,"source-file audit written",rows=len(D))

    summaries=[]
    for fam in PRIORITY:
        g=D[D["family"]==fam].copy()
        inspected=g[g["inspection_status"]=="INSPECTED"].copy() if len(g) else g
        max_year=None;min_year=None
        dates=[]
        for c in ["min_date","max_date"]:
            if c in inspected:
                z=pd.to_datetime(inspected[c],errors="coerce").dropna()
                dates.extend(z.tolist())
        if dates:
            min_year=min(x.year for x in dates);max_year=max(x.year for x in dates)
        v85f=int(fc.loc[fc["family"].astype(str).eq(fam),"features"].sum()) if len(fc) else 0
        if fam.startswith("cftc"):
            v85f=int(fc.loc[fc["family"].astype(str).str.startswith("cftc_"),"features"].sum())
        safely=int(g["safe_pre2023"].fillna(False).sum()) if len(g) else 0
        inspected_n=int((g["inspection_status"]=="INSPECTED").sum()) if len(g) else 0
        causal=int((g["has_available_at"].fillna(False)|g["has_release_semantics"].fillna(False)).sum()) if len(g) else 0
        reaches_2022=bool(max_year is not None and max_year>=2022)
        ready=bool(inspected_n>0 and reaches_2022 and causal>0)
        reason="READY" if ready else (
            "NO_CANDIDATE_FILES" if len(g)==0 else
            "NO_SAFE_INSPECTED_TABLE" if inspected_n==0 else
            "DOES_NOT_REACH_2022" if not reaches_2022 else
            "NO_CAUSAL_RELEASE_FIELD"
        )
        summaries.append({"family":fam,"candidate_files":int(len(g)),"safe_files":safely,"inspected_tables":inspected_n,
                          "v85_features":v85f,"min_year":min_year,"max_year":max_year,"causal_semantic_tables":causal,
                          "ready_for_research":ready,"reason":reason})
    S=pd.DataFrame(summaries)
    S.to_csv(out/"FAMILY_READINESS.csv",index=False)
    status(5,8,"family readiness assessed")

    recommendation="NO_READY_FAMILY"
    for fam in PRIORITY:
        r=S[S["family"]==fam]
        if len(r) and bool(r.iloc[0]["ready_for_research"]):
            recommendation=fam;break

    # Preserve exact V85 taxonomy evidence for all relevant families.
    relevant=fc[fc["family"].astype(str).str.contains("financial_conditions|treasury_auctions|alfred|cfe|cboe",regex=True,na=False)]
    relevant.to_csv(out/"V85_RELEVANT_FAMILIES.csv",index=False)

    status(6,8,"recommendation selected",recommended_next_family=recommendation)
    report=["# GEF V106 — Remaining causal-source audit","",f"Run: {rid}","",
            "## Family readiness","",S.to_markdown(index=False),"",
            f"Recommended next family: **{recommendation}**","",
            "No edge trials were run. No 2023+ market returns were read."]
    (out/"V106_REPORT.md").write_text("\n".join(report),encoding="utf-8")

    receipt={"run_id":rid,"status":"COMPLETE_V106_REMAINING_SOURCE_AUDIT","engine_version":ENGINE_VERSION,
             "source_v85":v85.name,"candidate_source_files":int(len(D)),"families_audited":PRIORITY,
             "recommended_next_family":recommendation,"edge_trials":0,
             "2023_2025_market_returns_accessed":False,"2026_accessed":False,
             "next":"BUILD_NEXT_FAMILY_ONLY_FROM_AUDITED_READY_SOURCE"}
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(7,8,"receipt/report written")
    status(8,8,"DONE")
    print("\n=== V106 RECEIPT ===");print(json.dumps(receipt,indent=2))
    print("\n=== V106 FAMILY READINESS ===");print(S.to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
