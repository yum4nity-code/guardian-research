#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path


def run(cmd, timeout=60):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)

def norm(s): return os.path.normcase(os.path.normpath(str(s or "")))

def terminal_processes():
    ps = "$p=@(Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object ProcessId,ExecutablePath); $p | ConvertTo-Json -Compress"
    cp=run(["powershell.exe","-NoProfile","-Command",ps],30)
    if cp.returncode: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    if not cp.stdout.strip(): return []
    o=json.loads(cp.stdout); return o if isinstance(o,list) else [o]

def utc(y,m,d,h=0,mi=0): return datetime(y,m,d,h,mi,tzinfo=timezone.utc)

def probe_window(mt5,symbol,start,end):
    ticks=mt5.copy_ticks_range(symbol,start,end,mt5.COPY_TICKS_ALL)
    err=mt5.last_error()
    if ticks is None or len(ticks)==0:
        return {"start":start.isoformat(),"end":end.isoformat(),"count":0,"last_error":err}
    times=[int(x["time_msc"]) for x in ticks]
    bids=[float(x["bid"]) for x in ticks if float(x["bid"])>0]
    return {"start":start.isoformat(),"end":end.isoformat(),"count":len(ticks),"first_utc":datetime.fromtimestamp(min(times)/1000,tz=timezone.utc).isoformat(),"last_utc":datetime.fromtimestamp(max(times)/1000,tz=timezone.utc).isoformat(),"positive_bid_ticks":len(bids),"last_error":err}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--terminal-exe",required=True); ap.add_argument("--output",required=True); ap.add_argument("--symbol-root",default="XAUUSD"); a=ap.parse_args()
    terminal=Path(a.terminal_exe)
    procs=terminal_processes()
    if len(procs)!=1 or norm(procs[0].get("ExecutablePath"))!=norm(terminal): raise RuntimeError(f"expected sole canonical terminal, got {procs}")
    import MetaTrader5 as mt5
    if not mt5.initialize(str(terminal),timeout=60000,portable=True): raise RuntimeError(f"initialize failed {mt5.last_error()}")
    try:
        ai=mt5.account_info(); ti=mt5.terminal_info()
        if ai is None or ti is None: raise RuntimeError(f"terminal/account unavailable {mt5.last_error()}")
        symbol=a.symbol_root if mt5.symbol_select(a.symbol_root,True) else None
        if not symbol:
            matches=sorted(str(s.name) for s in (mt5.symbols_get() or []) if str(s.name).startswith(a.symbol_root))
            if len(matches)!=1: raise RuntimeError(f"symbol resolution {matches[:20]}")
            symbol=matches[0]; mt5.symbol_select(symbol,True)
        windows=[
            (utc(2024,1,5,13,20),utc(2024,1,5,13,40)),
            (utc(2024,7,5,12,20),utc(2024,7,5,12,40)),
            (utc(2025,1,10,13,20),utc(2025,1,10,13,40)),
            (utc(2025,7,3,12,20),utc(2025,7,3,12,40)),
        ]
        probes=[probe_window(mt5,symbol,s,e) for s,e in windows]
        ok=all(p["count"]>0 and p["positive_bid_ticks"]>0 for p in probes)
        out={"schema":1,"status":"PASS" if ok else "FAIL","generated_at_utc":datetime.now(timezone.utc).isoformat(),"server":str(ai.server),"symbol":symbol,"terminal_maxbars":getattr(ti,"maxbars",None),"probes":probes,"historical_tick_path_viable":ok,"protected_2026_untouched":True}
        p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(out,indent=2,sort_keys=True))
        return 0 if ok else 2
    finally: mt5.shutdown()
if __name__=="__main__": raise SystemExit(main())
