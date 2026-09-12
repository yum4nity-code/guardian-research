#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
EXPECTED={
 'BTCUSDT_spot_5m_2017_2025.csv':'75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8',
 'ETHUSDT_spot_5m_2017_2025.csv':'21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',required=True); a=ap.parse_args(); root=Path(a.data_dir); got={}
 for name,want in EXPECTED.items():
  p=root/name
  if not p.is_file(): raise RuntimeError(f'missing pinned input: {p}')
  got[name]=sha(p)
  if got[name]!=want: raise RuntimeError(f'input hash mismatch {name}: {got[name]} != {want}')
 print(json.dumps({'status':'PASS','pinned_inputs':got,'note':'byte hashes only; no market rows or 2026 data inspected'},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
