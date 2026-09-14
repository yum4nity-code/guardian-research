#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, lzma, os, struct
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

START=date(2004,11,8)
END_EXCLUSIVE=date(2026,1,1)
NY=ZoneInfo("America/New_York")
NEEDED={"11:30","12:00","15:30","16:00"}

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda:f.read(1<<20),b""): h.update(ch)
    return h.hexdigest()

def atomic_json(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(t,p)

def iter_days(a,b):
    d=a
    while d<b:
        if d.weekday()<5: yield d
        d+=timedelta(days=1)

def decode(d:date,p:Path):
    payload=p.read_bytes()
    raw=lzma.decompress(payload)
    if len(raw)%24: raise RuntimeError(f"bad payload length {p}")
    base=datetime(d.year,d.month,d.day,tzinfo=timezone.utc)
    out={}
    for off in range(0,len(raw),24):
        sec,op=struct.unpack_from(">II",raw,off)
        if not (0<=sec<86400) or op<=0: raise RuntimeError(f"bad record {p}")
        ts=base+timedelta(seconds=int(sec))
        loc=ts.astimezone(NY); hm=loc.strftime("%H:%M")
        if hm in NEEDED:
            out[hm]={"ts":ts.isoformat(),"open":int(op),"date_ny":loc.date().isoformat()}
    return out

def locate(root:Path,d:date):
    p=root/f"{d.year:04d}"/f"{d.month:02d}"/f"{d.day:02d}.bi5"
    return p if p.exists() else None

def marker(root:Path,d:date):
    p=root/f"{d.year:04d}"/f"{d.month:02d}"/f"{d.day:02d}.missing.json"
    return p.exists()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inventory",required=True)
    ap.add_argument("--source-cache",required=True)
    ap.add_argument("--fast-cache",required=True)
    ap.add_argument("--output-dir",required=True)
    A=ap.parse_args()

    inv=json.loads(Path(A.inventory).read_text(encoding="utf-8"))
    known_missing=set(inv["known_missing_or_holiday_in_completed_prefix"])
    roots=[Path(A.source_cache),Path(A.fast_cache)]
    out=Path(A.output_dir); out.mkdir(parents=True,exist_ok=True)

    rows=[]; payloads=[]; missing=[]; dup_same=[]
    for d in iter_days(START,END_EXCLUSIVE):
        if d>=END_EXCLUSIVE: raise RuntimeError("protected 2026 reached")
        found=[p for p in (locate(r,d) for r in roots) if p]
        if len(found)>1:
            hs=[sha256(p) for p in found]
            if len(set(hs))!=1:
                raise RuntimeError(f"duplicate date hash mismatch {d}: {list(zip(map(str,found),hs))}")
            dup_same.append(d.isoformat())
        if found:
            p=found[0]; h=sha256(p); rec=decode(d,p)
            payloads.append({"date":d.isoformat(),"path":str(p.resolve()),"sha256":h,"bytes":p.stat().st_size})
            if NEEDED.issubset(rec):
                dates={rec[x]["date_ny"] for x in NEEDED}
                if len(dates)!=1: raise RuntimeError(f"NY date boundary split unexpected {d}: {dates}")
                dn=next(iter(dates))
                if dn>="2026-01-01": raise RuntimeError("protected 2026 boundary created")
                rows.append({
                  "date_ny":dn,
                  "ts_1130_utc":rec["11:30"]["ts"],"p_1130_raw":rec["11:30"]["open"],
                  "ts_1200_utc":rec["12:00"]["ts"],"p_1200_raw":rec["12:00"]["open"],
                  "ts_1530_utc":rec["15:30"]["ts"],"p_1530_raw":rec["15:30"]["open"],
                  "ts_1600_utc":rec["16:00"]["ts"],"p_1600_raw":rec["16:00"]["open"]
                })
        else:
            ds=d.isoformat()
            if ds in known_missing or marker(roots[1],d):
                missing.append(ds)
            else:
                raise RuntimeError(f"unresolved weekday neither payload nor missing marker: {ds}")

    df=pd.DataFrame(rows).sort_values("date_ny").drop_duplicates("date_ny")
    csv=out/"r15_dukascopy_xauusd_m1_boundaries_2004_2025.csv"; df.to_csv(csv,index=False)
    prov=out/"xauusd_dukascopy_master_payload_index.csv"; pd.DataFrame(payloads).to_csv(prov,index=False)
    manifest={
      "schema":3,"status":"PASS","phase":"r15-dukascopy-xauusd-boundary-union",
      "source":"Dukascopy XAUUSD BID M1 public historical feed",
      "cache_roots":[str(r.resolve()) for r in roots],
      "window":{"start":START.isoformat(),"end_exclusive":END_EXCLUSIVE.isoformat()},
      "payload_count":len(payloads),"known_missing_or_holiday_weekdays":len(missing),
      "eligible_boundary_days":int(len(df)),"duplicate_same_hash_dates":dup_same,
      "boundary_csv":str(csv.resolve()),"boundary_csv_sha256":sha256(csv),
      "payload_index_csv":str(prov.resolve()),"payload_index_csv_sha256":sha256(prov),
      "reuse_policy":"immutable multi-root M1 master cache; derive higher timeframes locally",
      "protected_2026_opened":False,
      "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    mp=out/"r15_dukascopy_market_manifest.json"; atomic_json(mp,manifest)
    print(json.dumps({"status":"PASS","payload_count":len(payloads),"missing_or_holiday":len(missing),
      "eligible_boundary_days":int(len(df)),"manifest":str(mp),"protected_2026_opened":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
