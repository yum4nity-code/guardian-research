#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil,subprocess,time,os
from pathlib import Path
from datetime import datetime,timezone

def atomic(p:Path,o:dict):
 p.parent.mkdir(parents=True,exist_ok=True); payload=json.dumps(o,indent=2,sort_keys=True)+'\n'; t=p.with_suffix(p.suffix+'.tmp')
 for _ in range(20):
  try:t.write_text(payload,encoding='utf-8'); os.replace(t,p); return
  except PermissionError: time.sleep(.1)
 p.write_text(payload,encoding='utf-8')

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); ap.add_argument('--target-source',required=True); ap.add_argument('--metaeditor',required=True); ap.add_argument('--target-ex5',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
 src=Path(a.source); dst=Path(a.target_source); ex5=Path(a.target_ex5); out=Path(a.output)
 if not src.exists(): raise RuntimeError(f'source missing: {src}')
 dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
 log=out.with_suffix('.compile.log'); cmd=[a.metaeditor,f'/compile:{dst}',f'/log:{log}']
 cp=subprocess.run(cmd,text=True,capture_output=True,check=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 txt=log.read_text(encoding='utf-16',errors='ignore') if log.exists() else (cp.stdout+'\n'+cp.stderr)
 ok=ex5.exists() and ('0 errors' in txt.lower())
 result={'schema':1,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'source':str(src),'target_source':str(dst),'target_ex5':str(ex5),'metaeditor_exit_code':cp.returncode,'compile_zero_errors':('0 errors' in txt.lower()),'compiled_exists':ex5.exists(),'status':'PASS' if ok else 'FAIL','note':'Preparation only; does not launch MT5 or execute the script.'}
 atomic(out,result)
 if not ok: raise RuntimeError('exporter compile failed')
 return 0
if __name__=='__main__': raise SystemExit(main())
