#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,os,subprocess,sys,time
from datetime import datetime,timezone,timedelta
from pathlib import Path

PHASE="phase-ib-xau-dataset"
FIELDS=["symbol","timeframe","server_time","server_epoch","open","high","low","close","tick_volume","spread","real_volume"]

def run(cmd,cwd=None,timeout=None): return subprocess.run(cmd,cwd=str(cwd) if cwd else None,text=True,capture_output=True,timeout=timeout,check=False)
def norm(s): return os.path.normcase(os.path.normpath(str(s or "")))
def parse_iso(s):
    d=datetime.fromisoformat(str(s).replace("Z","+00:00")); return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
def parse_wall(s): return datetime.strptime(str(s),"%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
def derive_offset(ia):
    m=ia["terminal_manifest"]; raw=(parse_wall(m["exported_at_server_time"])-parse_iso(ia["generated_at_utc"]).astimezone(timezone.utc)).total_seconds(); rounded=int(round(raw/3600)*3600)
    if abs(raw-rounded)>120 or abs(rounded)>14*3600: raise RuntimeError(f"unstable server offset raw={raw} rounded={rounded}")
    return rounded

def terminal_processes():
    ps="$p=@(Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object ProcessId,ExecutablePath); $p | ConvertTo-Json -Compress"
    cp=run(["powershell.exe","-NoProfile","-Command",ps],timeout=30)
    if cp.returncode: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    if not cp.stdout.strip(): return []
    o=json.loads(cp.stdout); return o if isinstance(o,list) else [o]

def write_progress(path,done,total,day,rows1,rows5,status="RUNNING"):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps({"schema":1,"phase":"I-B-TICK-REBUILD","status":status,"completed":done,"total":total,"day":day,"m1_rows":rows1,"m5_rows":rows5,"updated_at_utc":datetime.now(timezone.utc).isoformat()},indent=2,sort_keys=True)+"\n",encoding="utf-8")

def publish(pub,status,summary,arts,cwd):
    cmd=[sys.executable,str(pub),"--phase",PHASE,"--status",status,"--summary",summary]
    for a in arts:
        if a.exists(): cmd += ["--artifact",str(a)]
    cp=run(cmd,cwd,300)
    if cp.returncode: raise RuntimeError(f"publish failed: {cp.stderr.strip() or cp.stdout[-3000:]}")

def fetch_day(mt5,symbol,start,end,retries=12):
    last=None
    for i in range(retries):
        ticks=mt5.copy_ticks_range(symbol,start,end,mt5.COPY_TICKS_ALL); last=mt5.last_error()
        if ticks is not None:
            return ticks
        time.sleep(min(8,1+i*.75))
    raise RuntimeError(f"tick fetch failed {start.isoformat()} last_error={last}")

def update_bar(d,key,price,spread):
    b=d.get(key)
    if b is None: d[key]=[price,price,price,price,1,spread]
    else:
        if price>b[1]: b[1]=price
        if price<b[2]: b[2]=price
        b[3]=price; b[4]+=1; b[5]=spread

def emit(writer,symbol,tf,bars):
    n=0
    for epoch in sorted(bars):
        o,h,l,c,v,s=bars[epoch]
        st=datetime.fromtimestamp(epoch,tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
        writer.writerow({"symbol":symbol,"timeframe":tf,"server_time":st,"server_epoch":epoch,"open":repr(o),"high":repr(h),"low":repr(l),"close":repr(c),"tick_volume":v,"spread":s,"real_volume":0}); n+=1
    return n

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--ia-dir",required=True); ap.add_argument("--output-dir",required=True); ap.add_argument("--terminal-exe",required=True); ap.add_argument("--deploy",required=True); ap.add_argument("--progress-file",required=True); a=ap.parse_args()
    ia_dir=Path(a.ia_dir); out=Path(a.output_dir); deploy=Path(a.deploy); progress=Path(a.progress_file); terminal=Path(a.terminal_exe)
    ia_summary_path=ia_dir/"phase_ia_summary.json"; ia_mask=ia_dir/"phase_ia_xauusd_merged_news_mask_2024_2025.csv"; builder=deploy/"research/phenomenon_discovery/build_xau_news_clean_dataset_v1_00.py"; checker=deploy/"research/phenomenon_discovery/check_xau_news_clean_dataset_v1_00.py"; publisher=deploy/"research/phenomenon_discovery/publish_phase_result_v1_00.py"
    for p in (ia_summary_path,ia_mask,builder,checker,publisher,terminal):
        if not p.exists(): raise RuntimeError(f"missing dependency {p}")
    ia=json.loads(ia_summary_path.read_text(encoding="utf-8")); offset=derive_offset(ia); itm=ia["terminal_manifest"]
    procs=terminal_processes()
    if len(procs)!=1 or norm(procs[0].get("ExecutablePath"))!=norm(terminal): raise RuntimeError(f"requires sole canonical open terminal: {procs}")
    original_pid=int(procs[0]["ProcessId"])
    import MetaTrader5 as mt5
    publish(publisher,"RUNNING",f"Phase I-B tick-history rebuild starting from sole open MT5 PID {original_pid}; bypassing chart MaxBars without restarting terminal; 2024-2025 only.",[],deploy)
    if not mt5.initialize(str(terminal),timeout=60000,portable=True): raise RuntimeError(f"initialize failed {mt5.last_error()}")
    try:
        ti=mt5.terminal_info(); ai=mt5.account_info()
        if ti is None or ai is None: raise RuntimeError(f"terminal/account unavailable {mt5.last_error()}")
        if str(ai.server)!=str(itm.get("server")) or norm(ti.path)!=norm(itm.get("terminal_path")) or norm(ti.data_path)!=norm(itm.get("terminal_data_path")): raise RuntimeError("I-A terminal/server provenance mismatch")
        symbol="XAUUSD" if mt5.symbol_select("XAUUSD",True) else None
        if not symbol:
            matches=sorted(str(s.name) for s in (mt5.symbols_get() or []) if str(s.name).startswith("XAUUSD"))
            if len(matches)!=1: raise RuntimeError(f"XAUUSD resolution {matches[:20]}")
            symbol=matches[0]; mt5.symbol_select(symbol,True)
        si=mt5.symbol_info(symbol); point=float(si.point) if si and float(si.point)>0 else 0.01
        start=datetime(2024,1,1,tzinfo=timezone.utc)-timedelta(seconds=offset); end=datetime(2026,1,1,tzinfo=timezone.utc)-timedelta(seconds=offset)
        days=(end.date()-start.date()).days+1; out.mkdir(parents=True,exist_ok=True)
        raw1=out/"xauusd_m1_2024_2025_raw.csv"; raw5=out/"xauusd_m5_2024_2025_raw.csv"
        n1=n5=0
        with raw1.open("w",newline="",encoding="utf-8") as f1, raw5.open("w",newline="",encoding="utf-8") as f5:
            w1=csv.DictWriter(f1,fieldnames=FIELDS); w5=csv.DictWriter(f5,fieldnames=FIELDS); w1.writeheader(); w5.writeheader()
            d=start.replace(hour=0,minute=0,second=0,microsecond=0); done=0
            while d<end:
                de=min(d+timedelta(days=1),end); ticks=fetch_day(mt5,symbol,d,de-timedelta(milliseconds=1)); b1={}; b5={}
                for t in ticks:
                    bid=float(t["bid"])
                    if bid<=0: continue
                    utc_epoch=int(t["time_msc"])//1000; se=utc_epoch+offset
                    if not (datetime(2024,1,1,tzinfo=timezone.utc).timestamp() <= se < datetime(2026,1,1,tzinfo=timezone.utc).timestamp()): continue
                    ask=float(t["ask"]); spr=max(0,int(round((ask-bid)/point))) if ask>0 else 0
                    update_bar(b1,se-se%60,bid,spr); update_bar(b5,se-se%300,bid,spr)
                n1 += emit(w1,symbol,"M1",b1); n5 += emit(w5,symbol,"M5",b5); done+=1; write_progress(progress,done,days,d.date().isoformat(),n1,n5); d=de
        if n1<500000 or n5<100000: raise RuntimeError(f"tick rebuild coverage too small M1={n1} M5={n5}")
        manifest=out/"xauusd_history_terminal_manifest.txt"
        vals={"schema":"1","phase":"I-B","symbol":symbol,"symbol_root":"XAUUSD","server":str(ai.server),"company":str(ai.company),"terminal_path":str(ti.path),"terminal_data_path":str(ti.data_path),"terminal_commondata_path":str(ti.commondata_path),"from_server_time":"2024.01.01 00:00:00","to_server_time_exclusive":"2026.01.01 00:00:00","exported_at_server_time":datetime.fromtimestamp(time.time()+offset,tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S"),"python_api_utc_to_server_offset_seconds":str(offset),"python_api_source":"MetaTrader5.copy_ticks_range aggregated to bid OHLC","m1_rows":str(n1),"m5_rows":str(n5)}
        manifest.write_text("".join(f"{k}={v}\n" for k,v in vals.items()),encoding="utf-8")
    finally: mt5.shutdown()
    cp=run([sys.executable,str(builder),"--raw-m1",str(raw1),"--raw-m5",str(raw5),"--ib-terminal-manifest",str(manifest),"--ia-summary",str(ia_summary_path),"--ia-mask",str(ia_mask),"--output-dir",str(out)],deploy,1800)
    if cp.returncode: raise RuntimeError(f"builder failed: {cp.stderr.strip() or cp.stdout[-5000:]}")
    cp=run([sys.executable,str(checker),"--input-dir",str(out),"--ia-mask",str(ia_mask)],deploy,1800)
    if cp.returncode: raise RuntimeError(f"checker failed: {cp.stderr.strip() or cp.stdout[-6000:]}")
    summary=out/"phase_ib_summary.json"; integ=out/"phase_ib_integrity.json"; audit=out/"phase_ib_news_exclusion_audit.csv"; data=json.loads(integ.read_text(encoding="utf-8"))
    if data.get("status")!="PASS": raise RuntimeError("integrity non-PASS")
    publish(publisher,"PASS","Phase I-B PASS via historical MT5 tick reconstruction from sole FundedNext terminal; M1/M5 bid OHLC rebuilt for 2024-2025, news mask applied, integrity PASS, 2026 untouched.",[summary,integ,audit,manifest],deploy)
    write_progress(progress,days,days,"done",n1,n5,"PASS"); print(json.dumps({"status":"PASS","M1":n1,"M5":n5,"offset_seconds":offset},indent=2)); return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as e: print(f"PHASE I-B TICK REBUILD FAIL: {e}",file=sys.stderr); raise
