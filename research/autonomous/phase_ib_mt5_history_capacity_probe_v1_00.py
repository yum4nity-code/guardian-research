#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd, timeout=60):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)


def norm(s):
    return os.path.normcase(os.path.normpath(str(s or "")))


def terminal_processes():
    ps = "$p=@(Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object ProcessId,ExecutablePath); $p | ConvertTo-Json -Compress"
    cp = run(["powershell.exe","-NoProfile","-Command",ps],30)
    if cp.returncode: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    if not cp.stdout.strip(): return []
    o=json.loads(cp.stdout)
    return o if isinstance(o,list) else [o]


def iso(epoch):
    return datetime.fromtimestamp(int(epoch),tz=timezone.utc).isoformat()


def sample(mt5,symbol,tf,tf_name,count):
    rates=mt5.copy_rates_from_pos(symbol,tf,0,count)
    err=mt5.last_error()
    if rates is None or len(rates)==0:
        return {"timeframe":tf_name,"requested":count,"returned":0,"last_error":err}
    times=[int(x["time"]) for x in rates]
    return {"timeframe":tf_name,"requested":count,"returned":len(rates),"newest_utc":iso(max(times)),"oldest_utc":iso(min(times)),"last_error":err}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--terminal-exe",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--symbol-root",default="XAUUSD")
    args=ap.parse_args()
    terminal=Path(args.terminal_exe)
    if not terminal.exists(): raise RuntimeError(f"missing terminal {terminal}")
    procs=terminal_processes()
    if len(procs)!=1: raise RuntimeError(f"expected exactly one terminal64.exe, found {len(procs)}")
    if norm(procs[0].get("ExecutablePath"))!=norm(terminal): raise RuntimeError(f"sole terminal is not canonical: {procs[0].get('ExecutablePath')}")
    pid=int(procs[0]["ProcessId"])
    import MetaTrader5 as mt5
    if not mt5.initialize(str(terminal),timeout=60000,portable=True): raise RuntimeError(f"initialize failed {mt5.last_error()}")
    try:
        ti=mt5.terminal_info(); ai=mt5.account_info()
        if ti is None or ai is None: raise RuntimeError(f"terminal/account unavailable {mt5.last_error()}")
        symbol=args.symbol_root if mt5.symbol_select(args.symbol_root,True) else None
        if not symbol:
            matches=sorted(s.name for s in (mt5.symbols_get() or []) if s.name.startswith(args.symbol_root))
            if len(matches)!=1: raise RuntimeError(f"symbol resolution {matches[:20]}")
            symbol=matches[0]; mt5.symbol_select(symbol,True)
        probes=[]
        for count in (1000,100000,600000,1200000):
            probes.append(sample(mt5,symbol,mt5.TIMEFRAME_M1,"M1",count))
        for count in (1000,100000,300000,600000):
            probes.append(sample(mt5,symbol,mt5.TIMEFRAME_M5,"M5",count))
        maxbars=getattr(ti,"maxbars",None)
        out={"schema":1,"status":"PASS","generated_at_utc":datetime.now(timezone.utc).isoformat(),"terminal_pid":pid,"terminal_path":str(ti.path),"data_path":str(ti.data_path),"server":str(ai.server),"symbol":symbol,"terminal_maxbars":maxbars,"probes":probes,"protected_2026_untouched":True}
        p=Path(args.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(out,indent=2,sort_keys=True))
        return 0
    finally:
        mt5.shutdown()

if __name__=="__main__":
    raise SystemExit(main())
