#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

NY=ZoneInfo("America/New_York")
PROTECTED=pd.Timestamp("2026-01-01",tz="UTC")
REPL0=pd.Timestamp("2017-01-01",tz="UTC")
REPL1=pd.Timestamp("2019-05-31",tz="UTC")
CONF1=pd.Timestamp("2025-01-01",tz="UTC")
PRE1=PROTECTED
COSTS={"E1":0.001,"STRESS":0.002}

def atomic_json(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
 t.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8"); os.replace(t,p)

def hb(p,d,t,s,e=None):
 if not p:return
 x={"completed":int(d),"total":int(t),"stage":s,"updated_at_utc":datetime.now(timezone.utc).isoformat()}; x.update(e or {}); atomic_json(p,x)

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def load_manifest(path):
 m=json.loads(Path(path).read_text(encoding="utf-8"))
 if m.get("status")!="PASS" or m.get("server")!="FundedNext-Server 2": raise RuntimeError("market manifest not provenance-clean")
 return m

def load_m1(data_dir,manifest):
 parts=[]
 meta=manifest.get("timeframes",{}).get("M1",{})
 for y in range(2017,2026):
  p=Path(data_dir)/f"xauusd_m1_{y}.csv"
  if "2026" in p.name: raise RuntimeError("protected filename forbidden")
  if not p.exists(): raise RuntimeError(f"missing M1 file {p}")
  exp=(meta.get(str(y)) or {}).get("sha256")
  if not exp or sha(p)!=exp: raise RuntimeError(f"M1 hash mismatch {y}")
  z=pd.read_csv(p)
  req={"server_epoch","open"}
  if not req.issubset(z.columns): raise RuntimeError(f"invalid M1 columns {y}")
  t=pd.to_datetime(pd.to_numeric(z.server_epoch,errors="raise").astype("int64"),unit="s",utc=True)
  q=pd.DataFrame({"time":t,"open":pd.to_numeric(z.open,errors="raise")})
  if (q.time>=PROTECTED).any(): raise RuntimeError("protected 2026 row present")
  parts.append(q)
 d=pd.concat(parts,ignore_index=True).sort_values("time").drop_duplicates("time").reset_index(drop=True)
 if d.time.duplicated().any() or not d.time.is_monotonic_increasing: raise RuntimeError("M1 sequence invalid")
 return d

def clock_table(m1):
 z=m1.copy()
 ny=z.time.dt.tz_convert(NY)
 z["date"]=ny.dt.date
 z["hm"]=ny.dt.strftime("%H:%M")
 z["weekday"]=ny.dt.weekday
 need={"11:30","12:00","15:30","16:00"}
 z=z[z.hm.isin(need)&(z.weekday<5)]
 piv=z.pivot_table(index="date",columns="hm",values="open",aggfunc="first")
 piv=piv.dropna(subset=sorted(need)).reset_index()
 piv["date_ts"]=pd.to_datetime(piv["date"].astype(str),utc=True)
 piv["r5"]=np.log(piv["12:00"]/piv["11:30"])
 piv["r13"]=np.log(piv["16:00"]/piv["15:30"])
 piv["simple_last_half"]=piv["16:00"]/piv["15:30"]-1.0
 return piv

def hac_reg(x,y):
 x=np.asarray(x,float); y=np.asarray(y,float); n=len(x)
 if n<3:return {"n":n,"alpha":None,"beta":None,"r2":None,"t":None,"p":1.0,"lag":None}
 X=np.column_stack([np.ones(n),x]); inv=np.linalg.inv(X.T@X); b=inv@(X.T@y); u=y-X@b
 lag=max(1,int(math.floor(4*(n/100.0)**(2/9))))
 S=np.zeros((2,2))
 for t in range(n): S+=u[t]*u[t]*np.outer(X[t],X[t])
 for L in range(1,min(lag,n-1)+1):
  w=1-L/(lag+1)
  G=np.zeros((2,2))
  for t in range(L,n): G+=u[t]*u[t-L]*np.outer(X[t],X[t-L])
  S+=w*(G+G.T)
 cov=inv@S@inv
 se=math.sqrt(max(float(cov[1,1]),0.0))
 tv=float(b[1]/se) if se>0 else None
 p=float(math.erfc(abs(tv)/math.sqrt(2))) if tv is not None else 1.0
 ssr=float(np.sum(u*u)); sst=float(np.sum((y-y.mean())**2)); r2=1-ssr/sst if sst>0 else None
 return {"n":n,"alpha":float(b[0]),"beta":float(b[1]),"r2":r2,"t":tv,"p":p,"lag":lag}

def stage(df,a,b):
 return df[(df.date_ts>=a)&(df.date_ts<b)].copy()

def trading_metrics(df):
 if df.empty:return {"n":0,"gross_mean":None,"gross_net":None,"E1_mean":None,"E1_net":None,"STRESS_mean":None,"STRESS_net":None,"stress_ex_best":None,"concentration":None}
 direction=np.where(df.r5.to_numpy(float)>0,1.0,-1.0)
 gross=direction*df.simple_last_half.to_numpy(float)
 e1=gross-COSTS["E1"]; st=gross-COSTS["STRESS"]
 ssort=np.sort(st); ex=float(ssort[:-1].sum()) if len(ssort)>1 else -1.0
 pos=st[st>0]; conc=float(pos.max()/pos.sum()) if len(pos) and pos.sum()>0 else 1.0
 return {"n":len(df),"gross_mean":float(gross.mean()),"gross_net":float(gross.sum()),"E1_mean":float(e1.mean()),"E1_net":float(e1.sum()),"STRESS_mean":float(st.mean()),"STRESS_net":float(st.sum()),"stress_ex_best":ex,"concentration":conc}

def publish(pub,status,summary,arts):
 if not pub:return
 c=["python",pub,"--phase","r15-xauusd-gld-intraday-momentum","--status",status,"--summary",summary]
 for a in arts:c+=["--artifact",str(a)]
 subprocess.run(c,check=True)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--market-dir",required=True); ap.add_argument("--market-manifest",required=True)
 ap.add_argument("--output-dir",required=True); ap.add_argument("--progress-file"); ap.add_argument("--publisher")
 A=ap.parse_args(); out=Path(A.output_dir); out.mkdir(parents=True,exist_ok=True); prog=Path(A.progress_file) if A.progress_file else None

 hb(prog,0,4,"load")
 man=load_manifest(A.market_manifest); m1=load_m1(A.market_dir,man); tbl=clock_table(m1)
 hb(prog,1,4,"replication_2017_2019")
 repl=stage(tbl,REPL0,REPL1); rr=hac_reg(repl.r5,repl.r13)
 repl_pass=rr["n"]>=250 and rr["beta"] is not None and rr["beta"]>0 and rr["p"]<=0.05

 conf=pd.DataFrame(); cr={"n":0,"beta":None,"p":1.0}; year_beta={}; conf_pass=False
 if repl_pass:
  hb(prog,2,4,"confirmation_2019_2024")
  conf=stage(tbl,REPL1,CONF1); cr=hac_reg(conf.r5,conf.r13)
  posyears=0
  for y in range(2020,2025):
   q=conf[(conf.date_ts>=pd.Timestamp(f"{y}-01-01",tz="UTC"))&(conf.date_ts<pd.Timestamp(f"{y+1}-01-01",tz="UTC"))]
   yr=hac_reg(q.r5,q.r13); year_beta[str(y)]=yr
   if yr["beta"] is not None and yr["beta"]>0:posyears+=1
  conf_pass=cr["n"]>=500 and cr["beta"] is not None and cr["beta"]>0 and cr["p"]<=0.05 and posyears>=4
 else:
  posyears=0

 econ={"n":0}; econ_pass=False
 if conf_pass:
  hb(prog,3,4,"economic_2019_2024")
  econ=trading_metrics(conf)
  econ_pass=econ["E1_mean"]>0 and econ["STRESS_mean"]>0 and econ["stress_ex_best"]>0 and econ["concentration"]<=0.35

 pre={"n":0}; h1={"n":0}; h2={"n":0}; pre_pass=False
 if econ_pass:
  y25=stage(tbl,CONF1,PRE1); pre=trading_metrics(y25)
  h1=trading_metrics(y25[y25.date_ts<pd.Timestamp("2025-07-01",tz="UTC")])
  h2=trading_metrics(y25[y25.date_ts>=pd.Timestamp("2025-07-01",tz="UTC")])
  pre_pass=pre["n"]>=100 and pre["E1_mean"]>0 and pre["STRESS_mean"]>0 and h1["E1_net"]>0 and h2["E1_net"]>0 and pre["stress_ex_best"]>0 and pre["concentration"]<=0.35

 funnel={"replication_pass":int(repl_pass),"confirmation_pass":int(conf_pass),"economic_pass":int(econ_pass),"preoos_survivors":int(pre_pass)}
 result={"schema":1,"method":"xauusd_gld_intraday_momentum_near_replication","source_paper_doi":"10.1016/j.resourpol.2020.101830","source_revision":"R15-v1.00","preregistration":"research/autonomous/R15_XAUUSD_GLD_INTRADAY_MOMENTUM_PREREGISTRATION_2026_09_13.md","generated_at_utc":datetime.now(timezone.utc).isoformat(),"protected_2026_opened":False,"paper_reference":{"asset":"GLD","sample":"2004-11-08/2019-05-30","predictor":"r5","target":"r13","beta":0.0436,"t":3.03,"r2":0.0049,"oos_r2":0.0026},"replication":rr,"replication_pass":repl_pass,"confirmation":cr,"confirmation_years":year_beta,"positive_confirmation_years_2020_2024":posyears,"confirmation_pass":conf_pass,"economic":econ,"economic_pass":econ_pass,"preoos_2025":pre,"preoos_h1":h1,"preoos_h2":h2,"survivor_count":int(pre_pass),"funnel":funnel}
 rp=out/"r15_xauusd_gld_intraday_momentum_result.json"; dp=out/"r15_xauusd_gld_intraday_momentum_daily.csv"
 atomic_json(rp,result); tbl[(tbl.date_ts>=REPL0)&(tbl.date_ts<PRE1)].to_csv(dp,index=False)
 hb(prog,4,4,"complete",{"survivors":int(pre_pass),**funnel})
 status="PASS" if pre_pass else "FAIL"
 summary=f"R15 XAUUSD/GLD intraday-momentum near-replication {status}: funnel={funnel}; protected 2026 untouched."
 publish(A.publisher,status,summary,[rp,dp])
 print(json.dumps({"status":status,"funnel":funnel,"replication":rr,"confirmation":cr,"survivors":int(pre_pass),"protected_2026_opened":False}))
 return 0

if __name__=="__main__": raise SystemExit(main())
