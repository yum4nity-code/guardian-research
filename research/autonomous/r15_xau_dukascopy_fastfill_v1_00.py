#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, lzma, os, shutil, struct, subprocess, tempfile, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

END_EXCLUSIVE=date(2026,1,1)
BASE="https://datafeed.dukascopy.com/datafeed/XAUUSD"
FILE_NAME="BID_candles_min_1.bi5"
UA="guardian-research-xau-fastfill/1.0"

def atomic_json(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(t,p)

def atomic_bytes(p:Path,b:bytes):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_bytes(b)
    os.replace(t,p)

def url_for(d:date)->str:
    if d>=END_EXCLUSIVE: raise RuntimeError("protected 2026 request forbidden")
    return f"{BASE}/{d.year:04d}/{d.month-1:02d}/{d.day:02d}/{FILE_NAME}"

def validate(d:date,payload:bytes):
    if not payload: raise RuntimeError("empty payload")
    raw=lzma.decompress(payload)
    if len(raw)%24: raise RuntimeError("malformed payload length")
    if not raw: raise RuntimeError("no records")
    for off in range(0,len(raw),24):
        sec,op=struct.unpack_from(">II",raw,off)
        if not (0<=sec<86400) or op<=0:
            raise RuntimeError(f"invalid candle record offset={off}")
    return len(raw)//24

def curl_fetch(url:str,timeout:int):
    curl=shutil.which("curl.exe") or shutil.which("curl")
    if not curl: return None,None,"curl unavailable"
    fd,tmp=tempfile.mkstemp(prefix="xau_ff_",suffix=".bi5"); os.close(fd)
    try:
        cmd=[curl,"--location","--silent","--show-error","--http1.1",
             "--connect-timeout","15","--max-time",str(timeout),
             "--retry","4","--retry-delay","1","--retry-all-errors",
             "--user-agent",UA,"--header","Connection: close",
             "--header","Accept-Encoding: identity",
             "--output",tmp,"--write-out","%{http_code}",url]
        flags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout+20,creationflags=flags)
        txt=(cp.stdout or "").strip()
        code=int(txt[-3:]) if len(txt)>=3 and txt[-3:].isdigit() else None
        payload=Path(tmp).read_bytes() if Path(tmp).exists() else b""
        if cp.returncode!=0:
            return code,None,(cp.stderr or f"curl rc={cp.returncode}").strip()
        return code,payload,None
    except Exception as e:
        return None,None,repr(e)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass

def urllib_fetch(url:str,timeout:int):
    try:
        req=urllib.request.Request(url,headers={"User-Agent":UA,"Connection":"close","Accept-Encoding":"identity"})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return int(getattr(r,"status",200) or 200),r.read(),None
    except urllib.error.HTTPError as e:
        return int(e.code),None,repr(e)
    except Exception as e:
        return None,None,repr(e)

def fetch_one(ds:str,dest:Path,timeout:int):
    d=date.fromisoformat(ds)
    if d>=END_EXCLUSIVE: raise RuntimeError("protected 2026 date in inventory")
    out=dest/f"{d.year:04d}"/f"{d.month:02d}"/f"{d.day:02d}.bi5"
    miss=dest/f"{d.year:04d}"/f"{d.month:02d}"/f"{d.day:02d}.missing.json"

    if out.exists():
        payload=out.read_bytes(); n=validate(d,payload)
        return {"date":ds,"status":"ok","transport":"cache_fastfill","records":n,
                "sha256":hashlib.sha256(payload).hexdigest(),"bytes":len(payload)}
    if miss.exists():
        return {"date":ds,"status":"missing","transport":"marker"}

    errs=[]
    for round_no in range(1,4):
        for name,fn in (("curl",curl_fetch),("urllib",urllib_fetch)):
            code,payload,err=fn(url_for(d),timeout)
            if code==404:
                atomic_json(miss,{"date":ds,"status":"missing","http_code":404,"transport":name})
                return {"date":ds,"status":"missing","transport":name}
            if code==200 and payload:
                try:
                    n=validate(d,payload)
                    atomic_bytes(out,payload)
                    return {"date":ds,"status":"ok","transport":name,"records":n,
                            "sha256":hashlib.sha256(payload).hexdigest(),"bytes":len(payload)}
                except Exception as e:
                    errs.append({"round":round_no,"transport":name,"error":"validation:"+repr(e)})
            else:
                errs.append({"round":round_no,"transport":name,"http_code":code,"error":err})
        time.sleep(min(8,1.5*(2**(round_no-1))))
    return {"date":ds,"status":"error","errors":errs[-6:]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inventory",required=True)
    ap.add_argument("--dest-cache",required=True)
    ap.add_argument("--progress-file",required=True)
    ap.add_argument("--workers",type=int,default=8)
    ap.add_argument("--timeout",type=int,default=75)
    A=ap.parse_args()

    inv=json.loads(Path(A.inventory).read_text(encoding="utf-8"))
    if inv.get("status")!="PASS" or inv.get("protected_2026_opened") is not False:
        raise RuntimeError("inventory not safe/PASS")
    dates=list(inv["to_fetch"])
    if any(date.fromisoformat(x)>=END_EXCLUSIVE for x in dates):
        raise RuntimeError("inventory includes protected 2026")

    dest=Path(A.dest_cache); dest.mkdir(parents=True,exist_ok=True)
    prog=Path(A.progress_file)
    total=len(dates)
    counts={"ok":0,"missing":0,"error":0}
    transports={}
    errors=[]
    completed=0
    atomic_json(prog,{"stage":"fastfill","completed":0,"total":total,"counts":counts,"protected_2026_opened":False})

    workers=max(1,min(int(A.workers),12))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs={ex.submit(fetch_one,ds,dest,A.timeout):ds for ds in dates}
        for fut in as_completed(futs):
            ds=futs[fut]
            try: r=fut.result()
            except Exception as e: r={"date":ds,"status":"error","errors":[{"error":repr(e)}]}
            st=r["status"]; counts[st]=counts.get(st,0)+1
            tr=r.get("transport")
            if tr: transports[tr]=transports.get(tr,0)+1
            if st=="error": errors.append(r)
            completed+=1
            if completed%25==0 or completed==total:
                atomic_json(prog,{
                  "stage":"fastfill","completed":completed,"total":total,
                  "counts":counts,"transport_counts":transports,
                  "last_completed_date":ds,"error_count":len(errors),
                  "protected_2026_opened":False,
                  "updated_at_utc":datetime.now(timezone.utc).isoformat()
                })

    result={
      "schema":1,"status":"PASS" if not errors else "INCOMPLETE",
      "inventory":str(Path(A.inventory).resolve()),
      "dest_cache":str(dest.resolve()),"workers":workers,
      "total_requested":total,"counts":counts,"transport_counts":transports,
      "errors":errors,"protected_2026_opened":False,
      "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    rp=dest.parent/"r15_fastfill_result.json"; atomic_json(rp,result)
    atomic_json(prog,{**result,"stage":"complete"})
    print(json.dumps({k:result[k] for k in ["status","total_requested","counts","transport_counts","protected_2026_opened"]}))
    return 0 if not errors else 2

if __name__=="__main__":
    raise SystemExit(main())
