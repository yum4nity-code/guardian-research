#!/usr/bin/env python3
"""Independent repo-side implementation of preregistered D023 London ORB M15 V0.

Uses the same M15 input contract and cost conventions as
analyze_d027_d028_price_action_v1.py. This does NOT supersede the originally
prepared d023_london_orb_m15_eventstudy.py; it is a transparent conformance
implementation so the locked D023 experiment is executable from the repo.
"""
from __future__ import annotations

import argparse, csv, hashlib, json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import analyze_d027_d028_price_action_v1 as core

@dataclass
class Trade023:
    symbol: str; trade_day: str; side: str
    signal_time_utc: str; entry_time_utc: str; exit_time_utc: str
    or_high: float; or_low: float; entry: float; stop: float; exit: float
    risk_price: float; gross_r: float; net_r: Optional[float]
    exit_reason: str; commission_complete: bool


def d023_for_symbol(symbol, bars, commission_rt, spread_mult=1.0, commission_mult=1.0):
    days=core.group_days(bars); out=[]
    for day in sorted(days):
        # Exactly the four opening-range bars 08:00, 08:15, 08:30, 08:45 London.
        orb=[core.bar_at(days,day,8,m) for m in (0,15,30,45)]
        if any(b is None for b in orb): continue
        or_hi=max(b.h for b in orb); or_lo=min(b.l for b in orb)
        if or_hi<=or_lo: continue
        bs=days[day]; sig=None; side=None
        for j,b in enumerate(bs):
            lt=b.t.astimezone(core.LONDON); mins=lt.hour*60+lt.minute
            if mins<9*60 or mins>=11*60: continue
            if b.c>or_hi: sig,side=j,"LONG"; break
            if b.c<or_lo: sig,side=j,"SHORT"; break
        if sig is None or sig+1>=len(bs): continue
        eb=bs[sig+1]; elt=eb.t.astimezone(core.LONDON)
        if elt.date().isoformat()!=day: continue
        ent=core.entry_px(side,eb,spread_mult); stop=or_lo if side=="LONG" else or_hi
        risk=ent-stop if side=="LONG" else stop-ent
        if risk<=0: continue
        xb=core.final_bar_by(days,day,16,0)
        if xb is None or xb.t<eb.t: continue
        xp=core.close_px(side,xb,spread_mult); reason="TIME"
        for b in bs[sig+1:]:
            if b.t>xb.t: break
            if core.stop_hit(side,b,stop,spread_mult): xb=b; xp=stop; reason="STOP"; break
        pnl=(xp-ent) if side=="LONG" else (ent-xp)
        gross_r=pnl/risk
        net_r=None if commission_rt is None else (pnl-commission_rt*commission_mult)/risk
        out.append(Trade023(symbol,day,side,bs[sig].t.isoformat(),eb.t.isoformat(),xb.t.isoformat(),or_hi,or_lo,ent,stop,xp,risk,gross_r,net_r,reason,commission_rt is not None))
    return out


def summarize(base,stress,start_day,end_day):
    complete=bool(base) and all(t.commission_complete for t in base)
    get=(lambda t:t.net_r) if complete else (lambda t:t.gross_r)
    syms=sorted({t.symbol for t in base})
    per={s:core.stats([get(t) for t in base if t.symbol==s]) for s in syms}
    yrs={y:core.stats([get(t) for t in base if t.trade_day.startswith(y)]) for y in sorted({t.trade_day[:4] for t in base})}
    agg=core.stats([get(t) for t in base])
    daily=core.daily_series(base,get,start_day,end_day); lower=core.block_bootstrap_lower(daily); conc=core.monthly_concentration(base,get)
    stress_complete=bool(stress) and all(t.commission_complete for t in stress)
    stress_sum=sum(t.net_r for t in stress) if stress_complete else None
    if not complete: verdict="COST_MODEL_INCOMPLETE"
    else:
        counts=len(syms)==4 and all(per[s].get("n",0)>=60 for s in syms) and agg.get("n",0)>=300
        pos=sum(per[s].get("sum",0)>0 for s in syms)>=3
        pfok=(agg.get("pf") or 0)>=1.20
        boot=lower is not None and lower>0
        cok=conc is not None and conc<=0.60
        sok=stress_sum is not None and stress_sum>0
        verdict="CANDIDATE" if all((counts,pos,pfok,boot,cok,sok)) else "REJECT_V0"
    return {"basis":"net_r" if complete else "gross_r","commission_complete":complete,"aggregate":agg,"per_symbol":per,"per_year":yrs,"daily_bootstrap_lower_95_one_sided":lower,"positive_month_concentration":conc,"stress_1p5_net_r_sum":stress_sum,"verdict":verdict,"user_large_edge_note":"Even CANDIDATE does not override the user's preference for ~+0.15R/trade or better before production."}


def write_csv(path,rows):
    if not rows:path.write_text("",encoding="utf-8"); return
    flds=list(asdict(rows[0]))
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=flds); w.writeheader()
        for r in rows:w.writerow(asdict(r))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",action="append",required=True); ap.add_argument("--commission",action="append",default=[]); ap.add_argument("--outdir",required=True); ap.add_argument("--preoos-guard",action="store_true"); a=ap.parse_args()
    im=core.parse_map(a.input,"input"); req={"EURUSD","GBPUSD","USDJPY","XAUUSD"}
    if set(im)!=req: raise ValueError(f"Exactly required {sorted(req)}; got {sorted(im)}")
    cm={s:float(v) for s,v in core.parse_map(a.commission,"commission").items()}; od=Path(a.outdir); od.mkdir(parents=True,exist_ok=True)
    loaded={}; prov={}
    for s,p0 in im.items():
        p=Path(p0); raw=p.read_bytes(); prov[s]={"path":str(p),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}; loaded[s]=core.load_bars(p,a.preoos_guard)
    start_day,end_day=core.common_coverage(loaded); base=[]; stress=[]
    for s,bars in loaded.items():
        c=cm.get(s); base+=d023_for_symbol(s,bars,c,1.0,1.0); stress+=d023_for_symbol(s,bars,c,1.5,1.5)
    write_csv(od/"D023_trades.csv",base); write_csv(od/"D023_trades_coststress_1p5.csv",stress)
    summary={"engine":"analyze_d023_orb_v1","status":"INDEPENDENT_CONFORMANCE_IMPLEMENTATION","locked_spec":"D023 London ORB M15 V0","frozen_bootstrap":{"seed":core.BOOT_SEED,"reps":core.BOOT_REPS,"block_days":core.BOOT_BLOCK},"oos_start":core.OOS_START.isoformat(),"preoos_guard":a.preoos_guard,"input_assumption":"UTC M15 bid OHLC; spread in price units","common_coverage_london":[start_day,end_day],"provenance":prov,"D023":summarize(base,stress,start_day,end_day)}
    (od/"D023_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8"); print(json.dumps(summary,indent=2,allow_nan=False))

if __name__=="__main__": main()
