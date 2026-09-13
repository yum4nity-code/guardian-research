#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ENGINE=HERE/"r15_xauusd_gld_intraday_momentum_v1_00.py"
spec=importlib.util.spec_from_file_location("r15",ENGINE); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def ok(x,msg):
 if not x: raise AssertionError(msg)

def synthetic_clock_days(n=300,start="2018-01-02"):
 days=pd.bdate_range(start,periods=n)
 rows=[]
 for k,d in enumerate(days):
  pred=((k%9)-4)/1000.0
  target=0.0001+0.25*pred
  base=1300.0
  p1130=base
  p1200=base*math.exp(pred)
  p1530=base
  p1600=base*math.exp(target)
  for hm,p in [("11:30",p1130),("12:00",p1200),("15:30",p1530),("16:00",p1600)]:
   local=pd.Timestamp(f"{d.date()} {hm}",tz="America/New_York")
   rows.append({"time":local.tz_convert("UTC"),"open":p})
 return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)

def test_clock_mapping():
 t=m.clock_table(synthetic_clock_days())
 ok(len(t)==300,"eligible day count wrong")
 ok(abs(float(t.r5.iloc[0])-(-0.004))<1e-12,"r5 clock mapping wrong")
 ok(abs(float(t.r13.iloc[0])-(0.0001+0.25*(-0.004)))<1e-12,"r13 clock mapping wrong")

def test_hac_positive_beta():
 t=m.clock_table(synthetic_clock_days())
 r=m.hac_reg(t.r5,t.r13)
 ok(r["n"]==300,"regression n wrong")
 ok(abs(r["beta"]-0.25)<1e-8,"beta wrong")
 ok(r["p"]<=0.05,"positive synthetic relation not significant")

def test_market_timing_sign():
 t=m.clock_table(synthetic_clock_days(20))
 met=m.trading_metrics(t)
 ok(met["n"]==20,"trade count wrong")
 ok(met["gross_mean"] is not None,"missing trading metric")
 ok(abs((met["gross_mean"]-met["E1_mean"])-0.001)<1e-12,"E1 cost wrong")
 ok(abs((met["gross_mean"]-met["STRESS_mean"])-0.002)<1e-12,"stress cost wrong")

def test_boundaries():
 ok(m.REPL0==pd.Timestamp("2017-01-01",tz="UTC"),"replication start drift")
 ok(m.REPL1==pd.Timestamp("2019-05-31",tz="UTC"),"replication end drift")
 ok(m.CONF1==pd.Timestamp("2025-01-01",tz="UTC"),"confirmation end drift")
 ok(m.PRE1==pd.Timestamp("2026-01-01",tz="UTC"),"protected boundary drift")

def test_no_2026_loader_loop():
 src=Path(ENGINE).read_text(encoding="utf-8")
 ok("range(2017,2026)" in src,"loader year guard changed")
 ok('if "2026" in p.name' in src,"protected filename guard missing")
 ok("PROTECTED" in src,"protected row guard missing")
 ok('"r15-xauusd-gld-intraday-momentum"' in src,"publisher phase wrong")

def main():
 for fn in [test_clock_mapping,test_hac_positive_beta,test_market_timing_sign,test_boundaries,test_no_2026_loader_loop]: fn()
 print('{"status":"PASS","tests":"R15 deterministic methodology/code preflight"}')

if __name__=="__main__": main()
