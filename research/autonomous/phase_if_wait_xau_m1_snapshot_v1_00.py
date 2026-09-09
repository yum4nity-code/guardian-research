#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time,hashlib
from pathlib import Path
from datetime import datetime,timezone

def atomic(p,o):
 p.parent.mkdir(parents=True,exist_ok=True); s=json.dumps(o,indent=2,sort_keys=True)+'\n'; t=p.with_suffix(p.suffix+'.tmp')
 for _ in range(20):
  try:t.write_text(s,encoding='utf-8'); os.replace(t,p); return
  except PermissionError: time.sleep(.1)
 p.write_text(s,encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def parse_manifest(p):
 d={}
 for ln in Path(p).read_text(encoding='utf-8',errors='ignore').splitlines():
  if '=' in ln:
   k,v=ln.split('=',1); d[k.strip()]=v.strip()
 return d
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--wait-seconds',type=int,default=10800); ap.add_argument('--progress-file',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
 csvp=Path(a.csv); manp=Path(a.manifest); prog=Path(a.progress_file); out=Path(a.output); start=time.time(); deadline=start+a.wait_seconds
 while not (csvp.exists() and manp.exists()):
  elapsed=int(time.time()-start); atomic(prog,{'completed':0,'total':1,'stage':'waiting_for_mt5_xau_snapshot','elapsed_seconds':elapsed,'wait_limit_seconds':a.wait_seconds,'updated_at_utc':datetime.now(timezone.utc).isoformat()})
  if time.time()>=deadline: raise RuntimeError('timed out waiting for MT5 XAU snapshot CSV/manifest')
  time.sleep(10)
 md=parse_manifest(manp)
 req={'symbol':'XAUUSD','period':'M1','from':'2026.01.01 00:00:00','to_exclusive':'2026.09.01 00:00:00','server':'FundedNext-Server 2'}
 for k,v in req.items():
  if md.get(k)!=v: raise RuntimeError(f'manifest mismatch {k}: {md.get(k)!r} != {v!r}')
 if md.get('terminal_data_path','').lower()!=r'd:\mt5_fundednext'.lower(): raise RuntimeError('wrong terminal_data_path')
 rows=int(md.get('rows','0'))
 if rows<150000: raise RuntimeError(f'too few exported M1 rows: {rows}')
 result={'schema':1,'status':'PASS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'csv':str(csvp),'csv_sha256':sha(csvp),'csv_size_bytes':csvp.stat().st_size,'manifest':str(manp),'manifest_sha256':sha(manp),'manifest_fields':md,'protected_window_frozen':'2026-01-01..2026-09-01 exclusive','scientific_hypothesis_changed':False}
 atomic(out,result); atomic(prog,{'completed':1,'total':1,'stage':'snapshot_ready','updated_at_utc':datetime.now(timezone.utc).isoformat()}); return 0
if __name__=='__main__': raise SystemExit(main())
