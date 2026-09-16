#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, lzma, struct, tempfile
from datetime import date
from pathlib import Path
import build_xau_m5_stage_slice_v1_00 as s

REC=struct.Struct('>IIIIIf')

def payload(path:Path,base:int=2000000):
    raw=bytearray()
    for i,sec in enumerate([0,60,120,180,240]):
        o=base+i*10; c=o+5; lo=o-2; hi=c+3; raw+=REC.pack(sec,o,c,lo,hi,1.0)
    path.write_bytes(lzma.compress(bytes(raw))); return hashlib.sha256(path.read_bytes()).hexdigest()

def test_slice_does_not_open_outside_stage_payload():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); p1=root/'2019.bi5'; p1.write_bytes(b'valid-selected'); p2=root/'2025.bi5'; p2.write_bytes(b'INVALID-MUST-NOT-OPEN')
        idx=root/'index.csv'
        with idx.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['date','path','sha256','bytes']); w.writeheader(); w.writerow({'date':'2019-06-28','path':str(p1),'sha256':'a'*64,'bytes':p1.stat().st_size}); w.writerow({'date':'2025-01-02','path':str(p2),'sha256':'0'*64,'bytes':p2.stat().st_size})
        opened=[]
        class M1:
            def __init__(self,e): self.epoch=e; self.open=2000.; self.high=2001.; self.low=1999.; self.close=2000.5
        def fake_decode(d,p,h,n):
            opened.append(str(p)); assert p==p1; return [M1(1561680000+i*60) for i in range(5)]
        def fake_agg(m1): return [(1561680000,2000.,2001.,1999.,2000.5)],0
        def fake_sha(p): return 'f'*64
        old=s._canonical_builder_api; s._canonical_builder_api=lambda:(fake_decode,fake_agg,fake_sha)
        try:
            out=root/'m5.csv'; r=s.build(idx,out,date(2004,11,8),date(2019,6,30))
        finally: s._canonical_builder_api=old
        assert r['status']=='PASS' and r['source_days']==1 and opened==[str(p1)]

def test_2026_index_hard_fails_even_outside_requested_stage():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); p=root/'x.bi5'; h=payload(p); idx=root/'index.csv'
        with idx.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['date','path','sha256','bytes']); w.writeheader(); w.writerow({'date':'2019-06-28','path':str(p),'sha256':h,'bytes':p.stat().st_size}); w.writerow({'date':'2026-01-02','path':str(p),'sha256':h,'bytes':p.stat().st_size})
        try: s.parse_selected_rows(idx,date(2004,11,8),date(2019,6,30))
        except RuntimeError as e: assert 'PROTECTED 2026' in str(e)
        else: raise AssertionError('2026 index row did not hard fail')

if __name__=='__main__':
    test_slice_does_not_open_outside_stage_payload(); test_2026_index_hard_fails_even_outside_requested_stage(); print('PASS: stage-sliced M5 builder tests')
