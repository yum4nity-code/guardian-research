#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, lzma, struct
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

START=date(2004,11,8)
END_EXCLUSIVE=date(2026,1,1)

def day_iter(a,b):
    d=a
    while d<b:
        if d.weekday()<5:
            yield d
        d += timedelta(days=1)

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda:f.read(1<<20),b""): h.update(ch)
    return h.hexdigest()

def parse_cache_date(root:Path,p:Path)->date:
    rel=p.relative_to(root)
    parts=rel.parts
    if len(parts)!=3 or p.suffix.lower()!=".bi5":
        raise RuntimeError(f"unexpected cache layout: {rel}")
    return date(int(parts[0]),int(parts[1]),int(p.stem))

def validate_payload(d:date,p:Path)->dict:
    payload=p.read_bytes()
    if not payload:
        raise RuntimeError(f"empty cache payload: {p}")
    try:
        raw=lzma.decompress(payload)
    except lzma.LZMAError as e:
        raise RuntimeError(f"LZMA decode failed for {p}") from e
    if len(raw)%24:
        raise RuntimeError(f"malformed 24-byte candle payload: {p} len={len(raw)}")
    n=len(raw)//24
    if n<1:
        raise RuntimeError(f"no candles in {p}")
    for off in range(0,len(raw),24):
        sec,op=struct.unpack_from(">II",raw,off)
        if not (0<=sec<86400) or op<=0:
            raise RuntimeError(f"invalid candle record in {p} at offset {off}")
    return {"date":d.isoformat(),"relative_path":p.relative_to(p.parents[2]).as_posix(),"bytes":len(payload),"sha256":sha256(p),"records":n}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cache-dir",required=True)
    ap.add_argument("--progress-file",required=True)
    ap.add_argument("--output",required=True)
    A=ap.parse_args()

    cache=Path(A.cache_dir)
    progress=json.loads(Path(A.progress_file).read_text(encoding="utf-8"))
    last_date=date.fromisoformat(progress["last_date"])
    if last_date>=END_EXCLUSIVE:
        raise RuntimeError("progress last_date enters protected 2026")
    if progress.get("stage")!="download_dukascopy_m1_boundaries":
        raise RuntimeError(f"unexpected progress stage: {progress.get('stage')}")

    valid={}
    invalid=[]
    for p in sorted(cache.rglob("*.bi5")):
        try:
            d=parse_cache_date(cache,p)
            if d>=END_EXCLUSIVE: raise RuntimeError(f"protected 2026+ payload present: {p}")
            meta=validate_payload(d,p)
            if d.isoformat() in valid and valid[d.isoformat()]["sha256"]!=meta["sha256"]:
                raise RuntimeError(f"duplicate date with different hashes inside cache: {d}")
            meta["relative_path"]=p.relative_to(cache).as_posix()
            valid[d.isoformat()]=meta
        except Exception as e:
            invalid.append({"path":str(p),"error":repr(e)})

    if invalid:
        raise RuntimeError("invalid cached payload(s): "+json.dumps(invalid[:10]))

    all_days=list(day_iter(START,END_EXCLUSIVE))
    known_missing=[]
    present_prefix=[]
    present_future=[]
    to_fetch=[]
    for d in all_days:
        ds=d.isoformat()
        if d<=last_date:
            if ds in valid: present_prefix.append(ds)
            else: known_missing.append(ds)
        else:
            if ds in valid: present_future.append(ds)
            else: to_fetch.append(ds)

    orphan_tmp=[str(p) for p in cache.rglob("*.tmp")]

    out={
      "schema":1,
      "status":"PASS",
      "start":START.isoformat(),
      "end_exclusive":END_EXCLUSIVE.isoformat(),
      "progress_snapshot":progress,
      "last_completed_date":last_date.isoformat(),
      "total_weekdays":len(all_days),
      "valid_payload_count":len(valid),
      "present_in_completed_prefix":len(present_prefix),
      "present_after_prefix_from_probe_or_other":len(present_future),
      "known_missing_or_holiday_in_completed_prefix_count":len(known_missing),
      "to_fetch_count":len(to_fetch),
      "known_missing_or_holiday_in_completed_prefix":known_missing,
      "to_fetch":to_fetch,
      "payloads":valid,
      "orphan_tmp_files":orphan_tmp,
      "protected_2026_opened":False,
      "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    Path(A.output).parent.mkdir(parents=True,exist_ok=True)
    Path(A.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in [
      "status","last_completed_date","total_weekdays","valid_payload_count",
      "known_missing_or_holiday_in_completed_prefix_count","to_fetch_count","protected_2026_opened"
    ]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
