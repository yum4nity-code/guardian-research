from pathlib import Path
import argparse, json, pandas as pd, numpy as np

MARKETS=["XAUUSD","XAGUSD","UDXUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","SPXUSD","NSXUSD","WTIUSD","BCOUSD"]
PHENOMENA={
"P01":["XAUUSD","UDXUSD"],
"P04_WTI":["USDCAD","UDXUSD","WTIUSD"],
"P04_BRENT":["USDCAD","UDXUSD","BCOUSD"],
"P06":["NSXUSD","SPXUSD"],
"P08":["UDXUSD","EURUSD","GBPUSD","AUDUSD","USDJPY","USDCHF","USDCAD"],
"P11":["XAUUSD","XAGUSD"],
"P12_XAU":["XAUUSD"],"P12_XAG":["XAGUSD"],"P12_EUR":["EURUSD"],"P12_GBP":["GBPUSD"],
"P12_JPY":["USDJPY"],"P12_AUD":["AUDUSD"],"P12_CAD":["USDCAD"],"P12_CHF":["USDCHF"],
"P12_SPX":["SPXUSD"],"P12_NSX":["NSXUSD"],"P12_WTI":["WTIUSD"],
}

def load_year(root,sym,year):
    p=root/"DataLake"/"raw"/"histdata"/sym/"M1"/f"{sym}_M1_{year}.parquet"
    if not p.exists(): return None
    d=pd.read_parquet(p)
    dc=next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]),None)
    pc=next((c for c in d.columns if str(c).lower()=="close"),None)
    if dc is None and isinstance(d.index,pd.DatetimeIndex):
        d=d.reset_index();dc=d.columns[0]
    if dc is None or pc is None: return None
    utc=pd.to_datetime(d[dc],errors="coerce")+pd.Timedelta(hours=5)
    px=pd.to_numeric(d[pc],errors="coerce")
    q=pd.DataFrame({"utc":utc,"px":px}).dropna()
    q=q[q["utc"].dt.year==year].sort_values("utc").drop_duplicates("utc",keep="last")
    return q

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root)
    rows=[]; availability={}
    for sym in MARKETS:
        year_sets={}
        all_hours=[]
        for y in range(2009,2023):
            q=load_year(root,sym,y)
            if q is None or q.empty:
                rows.append({"market":sym,"year":y,"file":False,"m1_rows":0,"distinct_days":0,"top_hour_rows":0,"first":None,"last":None})
                year_sets[y]=set(); continue
            hours=q[(q["utc"].dt.minute==0)&(q["utc"].dt.second==0)]["utc"]
            # A usable 60m-return decision hour requires price now and ~60m earlier.
            s=q.set_index("utc")["px"].resample("1h").last()
            r=s/s.shift(1)-1
            hidx=set(r[r.notna()].index)
            year_sets[y]=hidx; all_hours.extend(hidx)
            rows.append({"market":sym,"year":y,"file":True,"m1_rows":len(q),"distinct_days":q["utc"].dt.normalize().nunique(),
                         "top_hour_rows":len(hidx),"first":str(q["utc"].min()),"last":str(q["utc"].max())})
        availability[sym]=year_sets
    D=pd.DataFrame(rows)
    print("=== MARKET YEAR COVERAGE ===")
    print(D.to_string(index=False))

    overlap=[]
    for name,syms in PHENOMENA.items():
        for y in range(2009,2023):
            sets=[availability[s].get(y,set()) for s in syms]
            common=set.intersection(*sets) if sets and all(len(x)>0 for x in sets) else set()
            overlap.append({"phenomenon":name,"year":y,"markets":"+".join(syms),"common_usable_hours":len(common),
                            "common_distinct_days":len({x.normalize() for x in common})})
    O=pd.DataFrame(overlap)
    print("\n=== PHENOMENON COMMON COVERAGE ===")
    print(O.to_string(index=False))

    print("\n=== BEST CONTIGUOUS 4-YEAR WINDOWS BY COMMON DISTINCT DAYS ===")
    out=[]
    for name,g in O.groupby("phenomenon"):
        vals={int(r.year):int(r.common_distinct_days) for r in g.itertuples()}
        for start in range(2009,2020):
            yrs=list(range(start,start+4))
            score=sum(vals.get(y,0) for y in yrs)
            miny=min(vals.get(y,0) for y in yrs)
            out.append({"phenomenon":name,"start":start,"end":start+3,"sum_common_days":score,"min_year_days":miny})
    B=pd.DataFrame(out).sort_values(["phenomenon","sum_common_days","min_year_days"],ascending=[True,False,False])
    print(B.groupby("phenomenon").head(3).to_string(index=False))

if __name__=="__main__":
    main()
