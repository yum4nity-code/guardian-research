#!/usr/bin/env python3
"""Frozen cheap-fail event study for Guardian D027 and D028.

D027 = NR7 contraction -> next-day breakout.
D028 = London early-session -> late-session intraday momentum.

Input: exactly EURUSD/GBPUSD/USDJPY/XAUUSD M15 CSVs, UTC timestamps, bid OHLC,
spread in PRICE UNITS. Delimiter auto-detected (comma/semicolon).

Commission must be supplied as round-trip price units for each symbol to emit a
fully costed verdict. Without it the engine still emits diagnostics but verdict
is COST_MODEL_INCOMPLETE. No parameter search is performed.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, math, random, statistics
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

OOS_START = datetime(2026, 6, 28, tzinfo=timezone.utc)
LONDON = ZoneInfo("Europe/London")
BOOT_SEED = 20260905
BOOT_REPS = 5000
BOOT_BLOCK = 5

ALIASES = {
    "time": {"time", "timestamp", "datetime", "date_time", "utc", "utc_time"},
    "open": {"open", "o"}, "high": {"high", "h"}, "low": {"low", "l"},
    "close": {"close", "c"},
    "spread": {"spread", "spread_price", "spread_price_units"},
}

@dataclass
class Bar:
    t: datetime; o: float; h: float; l: float; c: float; spread: float

@dataclass
class Trade027:
    symbol: str; nr7_day: str; trade_day: str; side: str
    signal_time_utc: str; entry_time_utc: str; exit_time_utc: str
    ref_high: float; ref_low: float; entry: float; stop: float; exit: float
    risk_price: float; gross_r: float; net_r: Optional[float]
    exit_reason: str; commission_complete: bool

@dataclass
class Trade028:
    symbol: str; trade_day: str; side: str; early_return: float
    entry_time_utc: str; exit_time_utc: str; entry: float; exit: float
    gross_return: float; net_return: Optional[float]; commission_complete: bool


def sniff_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="strict")[:4096]
    try: return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error: return ";" if sample.count(";") > sample.count(",") else ","


def parse_dt(s: str) -> datetime:
    s=s.strip()
    for fmt in ("%Y.%m.%d %H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M:%S%z","%Y-%m-%d %H:%M:%S%z"):
        try:
            dt=datetime.strptime(s,fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except ValueError: pass
    raise ValueError(f"Unsupported timestamp {s!r}")


def resolve_columns(fieldnames: List[str]) -> Dict[str,str]:
    low={f.strip().lower():f for f in fieldnames}; out={}
    for logical, aliases in ALIASES.items():
        hit=next((low[a] for a in aliases if a in low),None)
        if hit is None: raise ValueError(f"Missing column {logical}; got {fieldnames}")
        out[logical]=hit
    return out


def load_bars(path: Path, preoos_guard: bool) -> List[Bar]:
    bars=[]; delim=sniff_delimiter(path); last=None
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f,delimiter=delim)
        if not r.fieldnames: raise ValueError(f"No header in {path}")
        c=resolve_columns(r.fieldnames)
        for row in r:
            if not row[c["time"]].strip(): continue
            t=parse_dt(row[c["time"]])
            if preoos_guard and t>=OOS_START: raise RuntimeError(f"OOS_GUARD_FAIL {path}: {t.isoformat()}")
            if last is not None and t<=last: raise RuntimeError(f"NON_CHRONOLOGICAL_INPUT {path}: {t.isoformat()} <= {last.isoformat()}")
            last=t
            o,h,l,cl,spr=(float(row[c[k]]) for k in ("open","high","low","close","spread"))
            vals=(o,h,l,cl,spr)
            if not all(math.isfinite(x) for x in vals) or spr<0 or h<max(o,cl,l) or l>min(o,cl,h):
                raise ValueError(f"Bad OHLC/spread {path} {t}")
            bars.append(Bar(t,o,h,l,cl,spr))
    if not bars: raise ValueError(f"No bars in {path}")
    return bars


def group_days(bars: List[Bar]) -> Dict[str,List[Bar]]:
    d={}
    for b in bars:
        lt=b.t.astimezone(LONDON)
        if lt.weekday()<5: d.setdefault(lt.date().isoformat(),[]).append(b)
    return d


def bar_at(days, day, hh, mm):
    for b in days.get(day,[]):
        lt=b.t.astimezone(LONDON)
        if lt.hour==hh and lt.minute==mm: return b
    return None


def final_bar_by(days, day, hh, mm=0):
    target=hh*60+mm; e=[]
    for b in days.get(day,[]):
        lt=b.t.astimezone(LONDON); start=lt.hour*60+lt.minute
        if start+15<=target: e.append(b)
    return e[-1] if e else None


def entry_px(side,b,spread_mult): return b.o + b.spread*spread_mult if side=="LONG" else b.o

def close_px(side,b,spread_mult): return b.c if side=="LONG" else b.c+b.spread*spread_mult

def stop_hit(side,b,stop,spread_mult): return b.l<=stop if side=="LONG" else b.h+b.spread*spread_mult>=stop


def d027_for_symbol(symbol,bars,commission_rt,spread_mult=1.0,commission_mult=1.0):
    days=group_days(bars); complete=[]
    for day in sorted(days):
        bs=days[day]
        if len(bs)<80: continue
        hi=max(b.h for b in bs); lo=min(b.l for b in bs)
        if hi>lo: complete.append((day,hi,lo))
    nr7={}
    for i in range(6,len(complete)):
        w=complete[i-6:i+1]; day,hi,lo=w[-1]; rs=[h-l for _,h,l in w]; r=hi-lo
        if r==min(rs) and rs.count(r)==1: nr7[day]=(hi,lo)
    idx={d:i for i,(d,_,_) in enumerate(complete)}; out=[]
    for d,(rh,rl) in nr7.items():
        i=idx[d]
        if i+1>=len(complete): continue
        td=complete[i+1][0]; bs=days[td]; sig=None; side=None
        for j,b in enumerate(bs):
            lt=b.t.astimezone(LONDON); m=lt.hour*60+lt.minute
            if m<420 or m>=960: continue
            if b.c>rh: sig,side=j,"LONG"; break
            if b.c<rl: sig,side=j,"SHORT"; break
        if sig is None or sig+1>=len(bs): continue
        eb=bs[sig+1]; elt=eb.t.astimezone(LONDON)
        if elt.date().isoformat()!=td or elt.hour*60+elt.minute>=960: continue
        ent=entry_px(side,eb,spread_mult); stop=rl if side=="LONG" else rh
        risk=ent-stop if side=="LONG" else stop-ent
        if risk<=0: continue
        xb=final_bar_by(days,td,16,0)
        if xb is None or xb.t<eb.t: continue
        xp=close_px(side,xb,spread_mult); reason="TIME"
        for b in bs[sig+1:]:
            if b.t>xb.t: break
            if stop_hit(side,b,stop,spread_mult): xb=b; xp=stop; reason="STOP"; break
        pnl=(xp-ent) if side=="LONG" else (ent-xp)
        gross_r=pnl/risk
        net_r=None if commission_rt is None else (pnl-commission_rt*commission_mult)/risk
        out.append(Trade027(symbol,d,td,side,bs[sig].t.isoformat(),eb.t.isoformat(),xb.t.isoformat(),rh,rl,ent,stop,xp,risk,gross_r,net_r,reason,commission_rt is not None))
    return out


def d028_for_symbol(symbol,bars,commission_rt,spread_mult=1.0,commission_mult=1.0):
    days=group_days(bars); out=[]
    for day in sorted(days):
        a=bar_at(days,day,8,0); b=bar_at(days,day,8,15); e=bar_at(days,day,16,30); x=bar_at(days,day,16,45)
        if any(z is None for z in (a,b,e,x)): continue
        early=b.c/a.o-1.0
        if early==0: continue
        side="LONG" if early>0 else "SHORT"; ent=entry_px(side,e,spread_mult); xp=close_px(side,x,spread_mult)
        pnl=(xp-ent) if side=="LONG" else (ent-xp)
        gross=pnl/ent
        net=None if commission_rt is None else (pnl-commission_rt*commission_mult)/ent
        out.append(Trade028(symbol,day,side,early,e.t.isoformat(),x.t.isoformat(),ent,xp,gross,net,commission_rt is not None))
    return out


def pf(vals):
    gp=sum(x for x in vals if x>0); gl=-sum(x for x in vals if x<0)
    return (math.inf if gp>0 else None) if gl==0 else gp/gl

def stats(vals):
    if not vals:return {"n":0}
    return {"n":len(vals),"sum":sum(vals),"mean":statistics.fmean(vals),"median":statistics.median(vals),"win_rate":sum(x>0 for x in vals)/len(vals),"pf":pf(vals),"min":min(vals),"max":max(vals)}

def weekdays(start:date,end:date):
    d=start
    while d<=end:
        if d.weekday()<5: yield d.isoformat()
        d+=timedelta(days=1)

def daily_series(trades, value_fn, start_day, end_day):
    by={d:0.0 for d in weekdays(date.fromisoformat(start_day),date.fromisoformat(end_day))}
    for t in trades: by[t.trade_day]=by.get(t.trade_day,0.0)+value_fn(t)
    return [by[k] for k in sorted(by)]

def block_bootstrap_lower(vals, reps=BOOT_REPS, block=BOOT_BLOCK, seed=BOOT_SEED):
    if len(vals)<20:return None
    rng=random.Random(seed); n=len(vals); means=[]
    for _ in range(reps):
        sample=[]
        while len(sample)<n:
            i=rng.randrange(n)
            for j in range(block): sample.append(vals[(i+j)%n])
        means.append(statistics.fmean(sample[:n]))
    means.sort(); return means[max(0,int(0.05*reps)-1)]

def monthly_concentration(trades,value_fn):
    m={}
    for t in trades:m[t.trade_day[:7]]=m.get(t.trade_day[:7],0.0)+value_fn(t)
    pos=[v for v in m.values() if v>0]
    return None if not pos else max(pos)/sum(pos)

def common_coverage(loaded):
    starts=[]; ends=[]
    for bars in loaded.values():
        days=[b.t.astimezone(LONDON).date() for b in bars if b.t.astimezone(LONDON).weekday()<5]
        starts.append(min(days)); ends.append(max(days))
    s=max(starts); e=min(ends)
    if s>e: raise RuntimeError("NO_COMMON_COVERAGE")
    return s.isoformat(),e.isoformat()

def summarize027(base,stress,start_day,end_day):
    complete=bool(base) and all(t.commission_complete for t in base); get=(lambda t:t.net_r) if complete else (lambda t:t.gross_r)
    syms=sorted({t.symbol for t in base}); per={s:stats([get(t) for t in base if t.symbol==s]) for s in syms}; yrs={y:stats([get(t) for t in base if t.trade_day.startswith(y)]) for y in sorted({t.trade_day[:4] for t in base})}; agg=stats([get(t) for t in base])
    daily=daily_series(base,get,start_day,end_day); lower=block_bootstrap_lower(daily); conc=monthly_concentration(base,get)
    stress_complete=bool(stress) and all(t.commission_complete for t in stress); stress_sum=sum(t.net_r for t in stress) if stress_complete else None
    if not complete: verdict="COST_MODEL_INCOMPLETE"
    else:
        counts=len(syms)==4 and all(per[s].get("n",0)>=40 for s in syms) and agg.get("n",0)>=200
        pos=sum(per[s].get("sum",0)>0 for s in syms)>=3; pfok=(agg.get("pf") or 0)>=1.20; meanok=agg.get("mean",-9)>=0.10
        yrok=bool(yrs) and all(v.get("sum",0)>=0 for v in yrs.values()); boot=lower is not None and lower>0; cok=conc is not None and conc<=0.60; sok=stress_sum is not None and stress_sum>0
        verdict="CANDIDATE" if all((counts,pos,pfok,meanok,yrok,boot,cok,sok)) else "REJECT_V0"
    return {"basis":"net_r" if complete else "gross_r","commission_complete":complete,"aggregate":agg,"per_symbol":per,"per_year":yrs,"daily_bootstrap_lower_95_one_sided":lower,"positive_month_concentration":conc,"stress_1p5_net_r_sum":stress_sum,"verdict":verdict}

def summarize028(base,stress,start_day,end_day):
    complete=bool(base) and all(t.commission_complete for t in base); get=(lambda t:t.net_return) if complete else (lambda t:t.gross_return)
    syms=sorted({t.symbol for t in base}); per={s:stats([get(t) for t in base if t.symbol==s]) for s in syms}; yrs={y:stats([get(t) for t in base if t.trade_day.startswith(y)]) for y in sorted({t.trade_day[:4] for t in base})}; agg=stats([get(t) for t in base])
    daily=daily_series(base,get,start_day,end_day); lower=block_bootstrap_lower(daily); conc=monthly_concentration(base,get)
    stress_complete=bool(stress) and all(t.commission_complete for t in stress); stress_sum=sum(t.net_return for t in stress) if stress_complete else None
    if not complete: verdict="COST_MODEL_INCOMPLETE"
    else:
        counts=len(syms)==4 and all(per[s].get("n",0)>=180 for s in syms) and agg.get("n",0)>=800
        pos=sum(per[s].get("sum",0)>0 for s in syms)>=3; pfok=(agg.get("pf") or 0)>=1.15; yrok=bool(yrs) and all(v.get("sum",0)>=0 for v in yrs.values()); boot=lower is not None and lower>0; cok=conc is not None and conc<=0.60; sok=stress_sum is not None and stress_sum>0
        verdict="CANDIDATE" if all((counts,pos,pfok,yrok,boot,cok,sok)) else "REJECT_V0"
    return {"basis":"net_return" if complete else "gross_return","commission_complete":complete,"aggregate":agg,"per_symbol":per,"per_year":yrs,"daily_bootstrap_lower_95_one_sided":lower,"positive_month_concentration":conc,"stress_1p5_net_return_sum":stress_sum,"verdict":verdict}

def write_csv(path,rows):
    if not rows:path.write_text("",encoding="utf-8"); return
    flds=list(asdict(rows[0]));
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=flds); w.writeheader(); [w.writerow(asdict(r)) for r in rows]

def parse_map(items,kind):
    out={}
    for z in items:
        if "=" not in z: raise ValueError(f"{kind} must be SYMBOL=value")
        s,v=z.split("=",1); out[s.upper()]=v
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",action="append",required=True); ap.add_argument("--commission",action="append",default=[]); ap.add_argument("--outdir",required=True); ap.add_argument("--preoos-guard",action="store_true"); a=ap.parse_args()
    im=parse_map(a.input,"input"); req={"EURUSD","GBPUSD","USDJPY","XAUUSD"}
    if set(im)!=req: raise ValueError(f"Exactly required {sorted(req)}; got {sorted(im)}")
    cm={s:float(v) for s,v in parse_map(a.commission,"commission").items()}; od=Path(a.outdir); od.mkdir(parents=True,exist_ok=True)
    loaded={}; prov={}
    for s,p0 in im.items():
        p=Path(p0); raw=p.read_bytes(); prov[s]={"path":str(p),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}; loaded[s]=load_bars(p,a.preoos_guard)
    start_day,end_day=common_coverage(loaded)
    b27=[];x27=[];b28=[];x28=[]
    for s,bars in loaded.items():
        c=cm.get(s); b27+=d027_for_symbol(s,bars,c,1.0,1.0); x27+=d027_for_symbol(s,bars,c,1.5,1.5); b28+=d028_for_symbol(s,bars,c,1.0,1.0); x28+=d028_for_symbol(s,bars,c,1.5,1.5)
    write_csv(od/"D027_trades.csv",b27); write_csv(od/"D027_trades_coststress_1p5.csv",x27); write_csv(od/"D028_trades.csv",b28); write_csv(od/"D028_trades_coststress_1p5.csv",x28)
    summary={"engine":"analyze_d027_d028_price_action_v1","frozen_bootstrap":{"seed":BOOT_SEED,"reps":BOOT_REPS,"block_days":BOOT_BLOCK},"oos_start":OOS_START.isoformat(),"preoos_guard":a.preoos_guard,"input_assumption":"UTC M15 bid OHLC; spread in price units","common_coverage_london":[start_day,end_day],"provenance":prov,"D027":summarize027(b27,x27,start_day,end_day),"D028":summarize028(b28,x28,start_day,end_day)}
    (od/"D027_D028_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8"); print(json.dumps(summary,indent=2,allow_nan=False))
if __name__=="__main__": main()
