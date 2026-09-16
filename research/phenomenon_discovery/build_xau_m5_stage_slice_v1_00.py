#!/usr/bin/env python3
"""Build a stage-bounded XAUUSD BID M5 slice from the immutable R15 master index.

Unlike the generic pre-2026 builder, this wrapper opens only payloads whose dates
fall inside the explicitly requested stage window. It is intended to preserve a
sealed 2025 while R21-R25 discovery/confirmation are in progress.
"""
from __future__ import annotations

import argparse, csv, os
from datetime import date, datetime, timezone
from pathlib import Path

PROTECTED_START=date(2026,1,1)

def parse_selected_rows(index_csv:Path,start:date,end:date)->list[dict[str,str]]:
    if start>end: raise RuntimeError('stage start after end')
    if end>=PROTECTED_START: raise RuntimeError('stage may not include protected 2026+')
    selected=[]; previous=None
    with index_csv.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); required={'date','path','sha256','bytes'}
        missing=required-set(r.fieldnames or [])
        if missing: raise RuntimeError(f'payload index missing columns: {sorted(missing)}')
        for row in r:
            d=date.fromisoformat(row['date'])
            if d>=PROTECTED_START: raise RuntimeError(f'PROTECTED 2026 index row encountered: {d}')
            if previous is not None and d<=previous: raise RuntimeError(f'non-increasing payload index date: {d} <= {previous}')
            previous=d
            if start<=d<=end: selected.append(row)
    if not selected: raise RuntimeError(f'no payload rows in requested window {start}..{end}')
    return selected

def _canonical_builder_api():
    from build_xau_m5_from_r15_master_v1_00 import decode_day, aggregate_m5, sha256
    return decode_day, aggregate_m5, sha256

def build(index_csv:Path,output_csv:Path,start:date,end:date)->dict:
    decode_day, aggregate_m5, sha256 = _canonical_builder_api()
    rows=parse_selected_rows(index_csv,start,end)
    tmp=output_csv.with_suffix(output_csv.suffix+'.tmp'); tmp.parent.mkdir(parents=True,exist_ok=True)
    total_m1=total_m5=dropped=0; prev_epoch=None
    with tmp.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['symbol','timeframe','server_time','server_epoch','open','high','low','close'])
        for row in rows:
            d=date.fromisoformat(row['date']); payload=Path(row['path'])
            m1=decode_day(d,payload,row['sha256'],int(row['bytes'])); m5,drop=aggregate_m5(m1)
            total_m1+=len(m1); dropped+=drop
            for epoch,o,h,l,c in m5:
                dt=datetime.fromtimestamp(epoch,tz=timezone.utc)
                if not start<=dt.date()<=end: raise RuntimeError(f'out-of-stage M5 emitted: {dt.isoformat()}')
                if prev_epoch is not None and epoch<=prev_epoch: raise RuntimeError(f'non-increasing M5 epoch: {epoch}')
                prev_epoch=epoch; total_m5+=1
                w.writerow(['XAUUSD','M5',dt.isoformat(),epoch,f'{o:.3f}',f'{h:.3f}',f'{l:.3f}',f'{c:.3f}'])
    os.replace(tmp,output_csv)
    return {'status':'PASS','stage_start':start.isoformat(),'stage_end':end.isoformat(),'source_days':len(rows),'decoded_m1':total_m1,'emitted_m5':total_m5,'dropped_partial_m5_buckets':dropped,'protected_2026_opened':False,'output':str(output_csv.resolve()),'output_sha256':sha256(output_csv)}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--index',required=True,type=Path); ap.add_argument('--output',required=True,type=Path); ap.add_argument('--start',required=True); ap.add_argument('--end',required=True); a=ap.parse_args()
    result=build(a.index,a.output,date.fromisoformat(a.start),date.fromisoformat(a.end))
    import json; print(json.dumps(result,indent=2,sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
