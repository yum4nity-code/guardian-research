#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
START=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()); END=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp())

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def atomic(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); s=json.dumps(o,indent=2,sort_keys=True)+'\n'
 try:t.write_text(s,encoding='utf-8'); os.replace(t,p)
 except OSError:p.write_text(s,encoding='utf-8')
def manifest(p):
 d={}
 for ln in Path(p).read_text(encoding='utf-8',errors='ignore').splitlines():
  if '=' in ln:
   k,v=ln.split('=',1); d[k.strip()]=v.strip()
 return d
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--wait-seconds',type=int,default=604800); ap.add_argument('--progress-file',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
 csvp=Path(a.csv); manp=Path(a.manifest); start=time.time()
 while not (csvp.exists() and manp.exists()):
  atomic(a.progress_file,{'completed':0,'total':1,'stage':'waiting_for_mt5_m5_snapshot','updated_at_utc':datetime.now(timezone.utc).isoformat()})
  if time.time()-start>=a.wait_seconds: raise RuntimeError('timed out waiting for MT5 XAU M5 snapshot CSV/manifest')
  time.sleep(10)
 md=manifest(manp)
 if md.get('symbol')!='XAUUSD' or md.get('period')!='M5' or md.get('from')!='2026.01.01 00:00:00' or md.get('to_exclusive')!='2026.09.01 00:00:00': raise RuntimeError(f'invalid M5 snapshot manifest: {md}')
 if md.get('terminal_data_path','').lower()!=r'd:\mt5_fundednext'.lower() or md.get('server')!='FundedNext-Server 2': raise RuntimeError(f'wrong terminal/server provenance: {md}')
 rows=0; first=None; last=None; janapr=0; mayaug=0; prev=None
 with csvp.open('r',encoding='utf-8',errors='strict',newline='') as f:
  r=csv.DictReader(f)
  req={'server_time','server_epoch','open','high','low','close','tick_volume','spread','real_volume'}
  if not req.issubset(set(r.fieldnames or [])): raise RuntimeError('M5 snapshot columns invalid')
  for row in r:
   t=int(row['server_epoch'])
   if t<START or t>=END or t%300: raise RuntimeError(f'M5 snapshot time outside frozen window/alignment: {t}')
   if prev is not None and t<=prev: raise RuntimeError('M5 snapshot timestamps not strictly increasing/unique')
   prev=t; first=t if first is None else first; last=t; rows+=1
   if t<int(datetime(2026,5,1,tzinfo=timezone.utc).timestamp()): janapr+=1
   else: mayaug+=1
 if rows<30000: raise RuntimeError(f'too few exported M5 rows: {rows}')
 if first is None or first>int(datetime(2026,1,7,tzinfo=timezone.utc).timestamp()): raise RuntimeError(f'M5 snapshot starts too late: {first}')
 if last is None or last<int(datetime(2026,8,25,tzinfo=timezone.utc).timestamp()): raise RuntimeError(f'M5 snapshot ends too early: {last}')
 if janapr<12000 or mayaug<12000: raise RuntimeError(f'insufficient subperiod coverage janapr={janapr} mayaug={mayaug}')
 out={'schema':1,'status':'PASS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'csv':str(csvp),'csv_sha256':sha(csvp),'manifest':str(manp),'manifest_sha256':sha(manp),'manifest_fields':md,'rows':rows,'first_epoch':first,'last_epoch':last,'jan_apr_rows':janapr,'may_aug_rows':mayaug,'transport_only':True,'scientific_hypothesis_changed':False}
 atomic(a.output,out); atomic(a.progress_file,{'completed':1,'total':1,'stage':'complete','updated_at_utc':datetime.now(timezone.utc).isoformat()}); print(json.dumps(out,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
