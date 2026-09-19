from pathlib import Path
import pandas as pd
import hashlib, json
from datetime import datetime, timezone

ROOT=Path(r"D:\MT5_Backtests\DataLake")
RAW=ROOT/"raw"/"cboe"/"cfe"/"cfevoloi_RAW.csv"
OUT=ROOT/"normalized"/"cboe_cfe_pre2023"
META=ROOT/"metadata"
SAFE=OUT/"cfe_volume_open_interest_PRE2023.parquet"
CORE=OUT/"cfe_core_volatility_products_PRE2023.parquet"
MANIFEST=META/"cboe_cfe_voloi_manifest_v2.json"
OUT.mkdir(parents=True,exist_ok=True); META.mkdir(parents=True,exist_ok=True)

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

print("=== CBOE CFE PARSER V2 ===")
print("SOURCE: EXISTING RAW FILE | NO DOWNLOAD")
print("RESEARCH HARD CAP: 2022-12-31")
if not RAW.exists(): raise RuntimeError(f"RAW FILE NOT FOUND: {RAW}")

df=pd.read_csv(RAW,skiprows=1,low_memory=False)
df.columns=[str(c).strip() for c in df.columns]
if "Date" not in df.columns: raise RuntimeError("EXPECTED Date COLUMN MISSING")
df["Date"]=pd.to_datetime(df["Date"],format="%m/%d/%Y",errors="coerce")
if df["Date"].isna().any(): raise RuntimeError(f"INVALID DATE ROWS: {int(df['Date'].isna().sum())}")
df=df.sort_values("Date").reset_index(drop=True)
if df["Date"].duplicated().any(): raise RuntimeError(f"DUPLICATE DATES: {int(df['Date'].duplicated().sum())}")

safe=df[df["Date"]<=pd.Timestamp("2022-12-31")].copy()
locked=int((df["Date"]>=pd.Timestamp("2023-01-01")).sum())
if safe.empty: raise RuntimeError("NO PRE-2023 DATA")
if (safe["Date"]>=pd.Timestamp("2023-01-01")).any(): raise RuntimeError("POST-2022 LEAK")

for c in safe.columns:
    if c!="Date": safe[c]=pd.to_numeric(safe[c],errors="coerce")

inventory=[]
for c in safe.columns:
    if c=="Date": continue
    x=safe[c].dropna()
    if x.empty: continue
    d=safe.loc[x.index,"Date"]
    inventory.append({"column":c,"observations":int(len(x)),"first_date":d.min().strftime("%Y-%m-%d"),"last_date":d.max().strftime("%Y-%m-%d"),"nonzero":int((x!=0).sum())})
inventory.sort(key=lambda z:z["observations"],reverse=True)

keywords=("VOLATILITY INDEX","VOL. INDEX","VOL INDEX","VOLATILITY","MINI-VIX")
core_cols=["Date"]+[c for c in safe.columns if c!="Date" and any(k in c.upper() for k in keywords) and safe[c].notna().any()]
core=safe[core_cols].copy()
safe.to_parquet(SAFE,index=False); core.to_parquet(CORE,index=False)

manifest={"source":"Cboe Futures Exchange","dataset":"CFE Daily Volume and Open Interest","parser_version":2,
"raw_file":str(RAW),"raw_sha256":sha256(RAW),"safe_file":str(SAFE),"safe_sha256":sha256(SAFE),
"core_file":str(CORE),"core_sha256":sha256(CORE),"raw_rows":int(len(df)),"safe_rows":int(len(safe)),
"post2022_rows_excluded":locked,"first_safe_date":safe["Date"].min().strftime("%Y-%m-%d"),
"last_safe_date":safe["Date"].max().strftime("%Y-%m-%d"),"raw_columns":int(len(df.columns)),
"usable_pre2023_columns":int(len(inventory)),"core_columns":int(len(core.columns)-1),
"research_max_date":"2022-12-31","post2022_research_access":False,"inventory":inventory,
"created_utc":datetime.now(timezone.utc).isoformat()}
MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")

print("RAW ROWS       :",f"{len(df):,}")
print("SAFE ROWS      :",f"{len(safe):,}")
print("EXCLUDED >=2023:",f"{locked:,}")
print("SAFE RANGE     :",safe["Date"].min().date(),"->",safe["Date"].max().date())
print("RAW COLUMNS    :",len(df.columns))
print("USABLE <=2022  :",len(inventory))
print("CORE VOL COLS  :",len(core.columns)-1)
print("\n=== TOP AVAILABLE SERIES ===")
for x in inventory[:30]: print(f"{x['observations']:6,d} | {x['first_date']} -> {x['last_date']} | {x['column']}")
print("\n=== GUARDIAN CORE VOLATILITY SERIES ===")
for c in core.columns[1:]: print(f"{int(core[c].notna().sum()):6,d} | {c}")
print("\nSAFE     :",SAFE)
print("CORE     :",CORE)
print("MANIFEST :",MANIFEST)
print("2023-2026 RESEARCH ACCESS: FALSE")
print("STATUS: COMPLETE")
