from pathlib import Path
import argparse, json, re, zipfile, tempfile, os
import pandas as pd
import numpy as np

ENGINE_VERSION="V108.0"

def write_json(p,o):
    p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_.-]+","_",str(s))[:180]

def year_tokens(p):
    return [int(x) for x in re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)",str(p))]

def safe_pre2023(p):
    s=str(p).lower()
    if "pre2023" in s or "pre_2023" in s:return True
    ys=year_tokens(p)
    return bool(ys) and max(ys)<=2022

def treasury_like(p):
    s=str(p).lower()
    keys=["treasury_auction","treasury auction","auction_date","bid_to_cover","bid-to-cover","competitive_accepted","auction"]
    return any(k in s for k in keys)

def read_one(path):
    ext=path.suffix.lower()
    if ext==".csv": return pd.read_csv(path,low_memory=False)
    if ext==".parquet": return pd.read_parquet(path)
    if ext in [".xls",".xlsx"]: return pd.read_excel(path)
    if ext==".json":
        try:return pd.read_json(path)
        except Exception:
            obj=json.loads(path.read_text(encoding="utf-8",errors="ignore"))
            if isinstance(obj,list):return pd.DataFrame(obj)
            if isinstance(obj,dict):
                for v in obj.values():
                    if isinstance(v,list) and v and isinstance(v[0],dict):return pd.DataFrame(v)
            return pd.DataFrame()
    if ext==".xml":
        try:return pd.read_xml(path)
        except Exception:return pd.DataFrame()
    return None

def candidate_date_cols(cols):
    out=[]
    for c in cols:
        z=str(c).lower()
        if any(k in z for k in ["auction_date","auction date","issue_date","issue date","date","timestamp","publish","release"]):
            out.append(c)
    return out

def choose_auction_date(d):
    cols=list(d.columns)
    prefs=["auction_date","auction date","auctiondate","auction_datetime","auction timestamp"]
    low={str(c).strip().lower():c for c in cols}
    for p in prefs:
        if p in low:
            z=pd.to_datetime(d[low[p]],errors="coerce")
            if z.notna().sum():return low[p],z
    for c in candidate_date_cols(cols):
        z=pd.to_datetime(d[c],errors="coerce")
        if z.notna().sum():
            return c,z
    return None,pd.Series(pd.NaT,index=d.index)

def inspect_df(d,label,path):
    cols=list(d.columns)
    dc,dates=choose_auction_date(d)
    min_date=dates.dropna().min() if dates.notna().any() else None
    max_date=dates.dropna().max() if dates.notna().any() else None
    numeric=[]
    for c in cols:
        v=pd.to_numeric(d[c],errors="coerce")
        if v.notna().sum()>=max(3,min(20,len(d)//10 if len(d) else 3)):
            numeric.append(str(c))
    return {
        "path":str(path),"member":label,"rows":int(len(d)),"columns":"|".join(map(str,cols[:160])),
        "auction_date_col":str(dc) if dc is not None else "",
        "min_date":str(min_date) if min_date is not None else None,
        "max_date":str(max_date) if max_date is not None else None,
        "numeric_columns":"|".join(numeric[:120]),
        "has_bid_to_cover":any("bid" in str(c).lower() and "cover" in str(c).lower() for c in cols),
        "has_high_yield_or_rate":any("high" in str(c).lower() and ("yield" in str(c).lower() or "rate" in str(c).lower()) for c in cols),
        "usable_date":bool(dc is not None and dates.notna().sum()>0)
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);dl=root/"DataLake"
    base=root/"Research"/"Autonomous"/"guardian_edge_factory_v108_treasury_source_forensic"
    base.mkdir(parents=True,exist_ok=True)
    rid="GEF108-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=base/rid;out.mkdir(parents=True,exist_ok=False)

    files=[p for p in dl.rglob("*") if p.is_file() and treasury_like(p)]
    audit=[];schemas=[];preview_parts=[]
    for p in files:
        row={"path":str(p),"safe_pre2023":safe_pre2023(p),"extension":p.suffix.lower()}
        if not row["safe_pre2023"]:
            row["status"]="SKIP_UNBOUNDED_WINDOW";audit.append(row);continue
        try:
            if p.suffix.lower()==".zip":
                with zipfile.ZipFile(p) as z:
                    members=[m for m in z.namelist() if Path(m).suffix.lower() in [".csv",".xls",".xlsx",".json",".xml"]]
                    row["status"]="ZIP_INSPECTED";row["members"]=len(members);audit.append(row)
                    for m in members[:50]:
                        data=z.read(m);suffix=Path(m).suffix
                        with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tf:
                            tf.write(data);tmp=Path(tf.name)
                        try:
                            d=read_one(tmp)
                        finally:
                            try:os.unlink(tmp)
                            except OSError:pass
                        if d is None or d.empty:continue
                        info=inspect_df(d,m,p);schemas.append(info)
                        dc=info["auction_date_col"]
                        if dc:
                            dates=pd.to_datetime(d[dc],errors="coerce")
                            q=d.loc[dates.notna()].copy();q["_auction_date"]=dates[dates.notna()]
                            q=q[q["_auction_date"].dt.year<=2022]
                            if len(q):
                                q["_source"]=str(p)+"::"+m
                                preview_parts.append(q.head(500))
            else:
                d=read_one(p)
                if d is None or d.empty:
                    row["status"]="EMPTY_OR_UNSUPPORTED";audit.append(row);continue
                info=inspect_df(d,p.name,p);schemas.append(info)
                row["status"]="INSPECTED";row["rows"]=len(d);audit.append(row)
                dc=info["auction_date_col"]
                if dc:
                    dates=pd.to_datetime(d[dc],errors="coerce")
                    q=d.loc[dates.notna()].copy();q["_auction_date"]=dates[dates.notna()]
                    q=q[q["_auction_date"].dt.year<=2022]
                    if len(q):
                        q["_source"]=str(p);preview_parts.append(q.head(500))
        except Exception as e:
            row["status"]="READ_ERROR";row["error"]=repr(e)[:500];audit.append(row)

    A=pd.DataFrame(audit);S=pd.DataFrame(schemas)
    A.to_csv(out/"TREASURY_SOURCE_AUDIT.csv",index=False)
    S.to_csv(out/"TREASURY_SCHEMA_CANDIDATES.csv",index=False)

    normalized_rows=0
    max_year=None;min_year=None
    usable_tables=0
    if preview_parts:
        P=pd.concat(preview_parts,ignore_index=True,sort=False)
        P["_auction_date"]=pd.to_datetime(P["_auction_date"],errors="coerce")
        P=P[P["_auction_date"].notna() & (P["_auction_date"].dt.year<=2022)].copy()
        P["_AVAILABLE_AT"]=P["_auction_date"].dt.normalize()+pd.Timedelta(days=1)
        P.to_csv(out/"TREASURY_NORMALIZED_PREVIEW.csv",index=False)
        normalized_rows=len(P)
        if len(P):
            min_year=int(P["_auction_date"].dt.year.min());max_year=int(P["_auction_date"].dt.year.max())
        usable_tables=int(S["usable_date"].fillna(False).sum()) if len(S) else 0

    ready=bool(normalized_rows>0 and max_year is not None and max_year>=2018 and usable_tables>0)
    status="COMPLETE_V108_TREASURY_SOURCE_READY" if ready else "COMPLETE_V108_TREASURY_SOURCE_NOT_READY"
    receipt={
        "run_id":rid,"status":status,"engine_version":ENGINE_VERSION,
        "candidate_files":len(files),"safe_files":int(A["safe_pre2023"].fillna(False).sum()) if len(A) else 0,
        "schema_candidates":len(S),"usable_date_tables":usable_tables,
        "normalized_preview_rows":int(normalized_rows),"min_year":min_year,"max_year":max_year,
        "recommended_next":"BUILD_V109_TREASURY_EVENT_LEVEL" if ready else "DO_NOT_RUN_ALPHA; FIX_SOURCE_PROVENANCE_OR_CHOOSE_ANOTHER_FAMILY",
        "edge_trials":0,"market_returns_accessed":False,"2023_plus_rows_in_preview":False
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    print("\n=== V108 RECEIPT ===");print(json.dumps(receipt,indent=2))
    if len(S):
        print("\n=== V108 SCHEMA CANDIDATES ===")
        print(S[["path","member","rows","auction_date_col","min_date","max_date","has_bid_to_cover","has_high_yield_or_rate","usable_date"]].to_string(index=False))
    print("\nRUN:",out)

if __name__=="__main__":
    main()
