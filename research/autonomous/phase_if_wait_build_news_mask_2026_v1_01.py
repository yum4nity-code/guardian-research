#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,os,time
from datetime import datetime,timezone
from pathlib import Path

START=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())
END=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp())

def write_json_resilient(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 payload=json.dumps(o,indent=2,sort_keys=True)+'\n'
 t=p.with_suffix(p.suffix+'.tmp')
 last=None
 for _ in range(20):
  try:
   t.write_text(payload,encoding='utf-8')
   os.replace(t,p)
   return
  except PermissionError as e:
   last=e
   time.sleep(0.1)
 try:
  p.write_text(payload,encoding='utf-8')
  return
 except OSError:
  if last: raise last
  raise

def read_manifest(p):
 d={}
 for line in p.read_text(encoding='utf-8',errors='replace').splitlines():
  if '=' in line:
   k,v=line.split('=',1); d[k.strip()]=v.strip()
 return d

def write_csv(p,rows,fields):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--raw-common',required=True); ap.add_argument('--manifest-common',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--progress-file'); ap.add_argument('--wait-seconds',type=int,default=10800); a=ap.parse_args()
 raw=Path(a.raw_common); manp=Path(a.manifest_common); out=Path(a.output_dir); hb=Path(a.progress_file) if a.progress_file else None
 deadline=time.time()+a.wait_seconds
 while time.time()<deadline:
  if raw.exists() and manp.exists(): break
  if hb: write_json_resilient(hb,{'completed':0,'total':1,'stage':'waiting_for_mt5_calendar_export','updated_at_utc':datetime.now(timezone.utc).isoformat()})
  time.sleep(2)
 if not raw.exists() or not manp.exists(): raise RuntimeError('timed out waiting for Phase I-F MT5 calendar export; run Scripts -> Guardian -> ExportNewsCalendarIF2026 once in the canonical open MT5')
 m=read_manifest(manp)
 if m.get('server')!='FundedNext-Server 2': raise RuntimeError(f"wrong server in exporter manifest: {m.get('server')}")
 if m.get('terminal_data_path','').rstrip('\\').lower()!=r'D:\MT5_FundedNext'.rstrip('\\').lower(): raise RuntimeError(f"wrong terminal data path: {m.get('terminal_data_path')}")
 if m.get('from_server_time')!='2026.01.01 00:00:00' or m.get('to_server_time_exclusive')!='2026.09.01 00:00:00': raise RuntimeError('calendar exporter manifest window differs from frozen I-F window')
 if m.get('currencies','').strip().upper()!='USD': raise RuntimeError('calendar exporter currencies differ from frozen USD-only mask')
 rows=[]
 with raw.open('r',newline='',encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):
   try: ep=int(r['server_epoch']); imp=int(r['importance'])
   except: continue
   if ep<START or ep>=END: raise RuntimeError(f'out-of-window calendar row encountered epoch={ep}')
   if imp!=3 or str(r.get('currency','')).strip().upper()!='USD': continue
   rows.append(r)
 if not rows: raise RuntimeError('no USD high-impact rows in frozen calendar export')
 seen=set(); events=[]; intervals=[]
 for r in sorted(rows,key=lambda x:int(x['server_epoch'])):
  vid=str(r.get('value_id','')).strip()
  if not vid or vid in seen: continue
  seen.add(vid); ep=int(r['server_epoch']); s=ep-300; e=ep+300
  events.append({'value_id':vid,'event_id':r.get('event_id',''),'server_time':r.get('server_time',''),'server_epoch':ep,'currency':'USD','importance':3,'event_name':r.get('event_name',''),'mask_start_server_epoch':s,'mask_end_server_epoch':e})
  intervals.append((s,e,vid))
 merged=[]
 for s,e,vid in intervals:
  if merged and s<=merged[-1]['mask_end_server_epoch']:
   merged[-1]['mask_end_server_epoch']=max(merged[-1]['mask_end_server_epoch'],e); merged[-1]['source_event_ids']+=';'+vid
  else: merged.append({'mask_start_server_epoch':s,'mask_end_server_epoch':e,'source_event_ids':vid})
 for i,r in enumerate(merged,1): r.update({'interval_id':i,'target_symbol':'XAUUSD','currency':'USD','research_profile':'PHASE_IF_USD_HIGH_IMPACT_PM5'})
 out.mkdir(parents=True,exist_ok=True)
 evp=out/'phase_if_xauusd_high_impact_events_2026_jan_aug.csv'; mkp=out/'phase_if_xauusd_merged_news_mask_2026_jan_aug.csv'; sump=out/'phase_if_news_mask_summary.json'
 write_csv(evp,events,['value_id','event_id','server_time','server_epoch','currency','importance','event_name','mask_start_server_epoch','mask_end_server_epoch'])
 write_csv(mkp,merged,['interval_id','target_symbol','currency','research_profile','mask_start_server_epoch','mask_end_server_epoch','source_event_ids'])
 summary={'schema':1,'phase':'I-F-NEWS-MASK','status':'PASS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'event_rows':len(events),'merged_intervals':len(merged),'window':{'start':'2026.01.01 00:00:00','end_exclusive':'2026.09.01 00:00:00'},'server':'FundedNext-Server 2','terminal_data_path':m.get('terminal_data_path'),'currency':'USD','pre_minutes':5,'post_minutes':5,'market_outcomes_opened':False,'scientific_hypothesis_changed':False}
 write_json_resilient(sump,summary)
 if hb: write_json_resilient(hb,{'completed':1,'total':1,'stage':'news_mask_frozen','updated_at_utc':datetime.now(timezone.utc).isoformat()})
 print(json.dumps(summary,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
