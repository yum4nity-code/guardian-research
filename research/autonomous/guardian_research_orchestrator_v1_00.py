#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, shutil, signal, subprocess, sys, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION="1.00"
DEFAULT_REMOTE="https://github.com/yum4nity-code/guardian-research.git"
DEFAULT_DEPLOY=r"D:\MT5_Backtests\guardian-autonomous-main"
DEFAULT_ROOT=r"D:\MT5_Backtests\Research\Autonomous"
QUEUE_REL=Path("research/autonomous/RESEARCH_QUEUE.json")
PUBLISHER_REL=Path("research/phenomenon_discovery/publish_phase_result_v1_00.py")
PROTECTED_2026_EPOCH=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())

def now(): return datetime.now(timezone.utc).isoformat()
def load_json(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def atomic_json(p:Path,obj:Any):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(t,p)
def run(cmd,cwd=None,timeout=None):
    return subprocess.run(cmd,cwd=str(cwd) if cwd else None,timeout=timeout,text=True,capture_output=True,check=False)
def git(repo:Path,*args,timeout=120):
    cp=run(["git",*args],repo,timeout)
    if cp.returncode: raise RuntimeError(f"git {' '.join(args)} failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")
    return cp.stdout.strip()
def ensure_clone(deploy:Path,remote:str):
    if not (deploy/".git").exists():
        deploy.parent.mkdir(parents=True,exist_ok=True)
        if deploy.exists(): shutil.rmtree(deploy)
        cp=run(["git","clone","--no-tags",remote,str(deploy)],timeout=300)
        if cp.returncode: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
    git(deploy,"fetch","origin","main","backtest-results","--prune",timeout=180)
    git(deploy,"checkout","-B","main","origin/main"); git(deploy,"reset","--hard","origin/main"); git(deploy,"clean","-fd")
    return git(deploy,"rev-parse","HEAD")
def remote_json(deploy:Path,ref:str,path:str):
    cp=run(["git","show",f"{ref}:{path}"],deploy,30)
    if cp.returncode: return None
    try: return json.loads(cp.stdout)
    except json.JSONDecodeError: return None
def relpath(s:str):
    p=Path(s.replace("\\","/"))
    if p.is_absolute() or ".." in p.parts: raise ValueError(f"unsafe repo path: {s}")
    return p

def validate_queue(q):
    if q.get("schema")!=1: raise ValueError("queue schema must be 1")
    allow2026=bool(q.get("human_approved_2026",False)); seen=set()
    for j in q.get("jobs",[]):
        for k in ("id","revision","enabled","executor"):
            if k not in j: raise ValueError(f"job missing {k}")
        key=(j["id"],j["revision"])
        if key in seen: raise ValueError(f"duplicate job {key}")
        seen.add(key)
        kind=j["executor"].get("kind")
        if kind not in {"noop","python","powershell","codex_assist"}: raise ValueError(f"unsupported executor {kind}")
        if kind in {"python","powershell"}: relpath(j["executor"].get("path",""))
        end=(j.get("data_window") or {}).get("end_exclusive")
        if end:
            dt=datetime.fromisoformat(end.replace("Z","+00:00")); dt=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            if int(dt.timestamp())>PROTECTED_2026_EPOCH and not allow2026: raise ValueError(f"{j['id']} opens protected 2026")

def p95(v):
    if not v:return None
    x=sorted(v)
    if len(x)==1:return x[0]
    pos=.95*(len(x)-1); lo=math.floor(pos); hi=math.ceil(pos)
    return x[lo] if lo==hi else x[lo]+(x[hi]-x[lo])*(pos-lo)
def history(path:Path,key:str):
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        try:r=json.loads(line)
        except:continue
        if r.get("class_key")==key and r.get("status")=="PASS":
            try:out.append(float(r["duration_seconds"]))
            except:pass
    return out[-50:]
def hard_limit(policy,hist,elapsed,fraction):
    vals=[float(policy.get("min_seconds",300))]; em=float(policy.get("eta_multiplier",2.5)); hm=float(policy.get("history_p95_multiplier",3.0))
    if policy.get("expected_seconds") is not None: vals.append(float(policy["expected_seconds"])*em)
    h=p95(hist)
    if h is not None: vals.append(h*hm)
    if fraction is not None and 0<fraction<1 and elapsed>0: vals.append((elapsed/fraction)*em)
    return max(vals)
def progress(path):
    if not path or not path.exists(): return None,None
    try:o=load_json(path)
    except:return None,path.stat().st_mtime
    try:
        total=float(o.get("total")); done=float(o.get("completed")); frac=max(0,min(1,done/total)) if total>0 else None
    except: frac=None
    return frac,path.stat().st_mtime
def dep_ok(dep,deploy,receipts):
    if dep.get("kind")=="github_result":
        o=remote_json(deploy,dep.get("ref","origin/backtest-results"),dep["path"])
        return (o is not None and o.get("status") in dep.get("accepted_status",["PASS"])), ("ok" if o else "remote result missing")
    if dep.get("kind")=="receipt":
        p=receipts/f"{dep['job_id']}__r{int(dep['revision'])}.json"
        if not p.exists():return False,"receipt missing"
        o=load_json(p); return o.get("status") in dep.get("accepted_status",["PASS"]),f"receipt status={o.get('status')}"
    raise ValueError(f"unsupported dependency {dep.get('kind')}")
def expand(s,root,deploy,jid): return str(s).replace("{ROOT}",str(root)).replace("{DEPLOY}",str(deploy)).replace("{JOB_ID}",jid)
def kill_tree(p):
    if p.poll() is not None:return
    try:
        if os.name=="nt": run(["taskkill","/PID",str(p.pid),"/T","/F"],timeout=30)
        else: os.killpg(os.getpgid(p.pid),signal.SIGTERM)
    except:
        try:p.kill()
        except:pass

@dataclass
class Result:
    status:str; exit_code:int|None; duration:float; reason:str; out:str; err:str; limit:float

def execute(job,deploy,root,histfile):
    ex=job["executor"]; kind=ex["kind"]
    if kind=="noop": return Result("PASS",0,0,"noop gate satisfied","","",0)
    if kind=="codex_assist": return Result("BLOCKED",None,0,"Codex adapter intentionally fail-closed in v1.00","","",0)
    target=(deploy/relpath(ex["path"])).resolve()
    if deploy.resolve() not in target.parents or not target.exists(): return Result("FAIL",None,0,f"executor missing/unsafe: {target}","","",0)
    args=[expand(a,root,deploy,job["id"]) for a in ex.get("args",[])]
    if kind=="python": cmd=[sys.executable,str(target),*args]
    else: cmd=[shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(target),*args]
    env=os.environ.copy(); env.update({"GUARDIAN_AUTONOMOUS_ROOT":str(root),"GUARDIAN_DEPLOY_ROOT":str(deploy),"GUARDIAN_JOB_ID":job["id"],"GUARDIAN_JOB_REVISION":str(job["revision"])})
    for k,v in ex.get("env",{}).items():env[str(k)]=expand(v,root,deploy,job["id"])
    logs=root/"logs"; logs.mkdir(parents=True,exist_ok=True); op=logs/f"{job['id']}__r{job['revision']}.out.log"; ep=logs/f"{job['id']}__r{job['revision']}.err.log"
    flags={"start_new_session":True} if os.name!="nt" else {}
    with op.open("w",encoding="utf-8") as out,ep.open("w",encoding="utf-8") as err:
        p=subprocess.Popen(cmd,cwd=str(deploy),env=env,text=True,stdout=out,stderr=err,**flags); start=time.monotonic(); pol=job.get("timeout",{}); hist=history(histfile,job.get("class_key",job["id"])); pf=pol.get("progress_file"); pp=Path(expand(pf,root,deploy,job["id"])) if pf else None; stale=float(pol.get("stale_heartbeat_seconds",900)); last=None; limit=hard_limit(pol,hist,0,None); timed=False; reason=""
        while p.poll() is None:
            elapsed=time.monotonic()-start; frac,mt=progress(pp); last=mt if mt and (last is None or mt>last) else last; limit=hard_limit(pol,hist,elapsed,frac)
            is_stale=(elapsed>stale if pp and last is None else (time.time()-last>stale if pp else elapsed>limit))
            if elapsed>limit and is_stale: timed=True; reason=f"adaptive timeout elapsed={elapsed:.1f}s limit={limit:.1f}s"; kill_tree(p); break
            time.sleep(max(1,float(pol.get("poll_seconds",5))))
        dur=time.monotonic()-start
    ot="\n".join(op.read_text(encoding="utf-8",errors="replace").splitlines()[-80:]); et="\n".join(ep.read_text(encoding="utf-8",errors="replace").splitlines()[-80:])
    if timed:return Result("TIMEOUT",p.poll(),dur,reason,ot,et,limit)
    return Result("PASS" if p.returncode==0 else "FAIL",p.returncode,dur,"executor exit 0" if p.returncode==0 else f"executor exit {p.returncode}",ot,et,limit)

def receipt(receipts,j):return receipts/f"{j['id']}__r{j['revision']}.json"
def append_hist(p,row): p.parent.mkdir(parents=True,exist_ok=True); open(p,"a",encoding="utf-8").write(json.dumps(row,sort_keys=True)+"\n")
def publish(deploy,health,rcpt,status,summary):
    pub=deploy/PUBLISHER_REL
    if not pub.exists():return
    mapped="RUNNING" if status in {"RUNNING","WAITING","IDLE"} else ("PASS" if status=="PASS" else "FAIL")
    cmd=[sys.executable,str(pub),"--phase","autonomous-research-orchestrator","--status",mapped,"--summary",summary,"--artifact",str(health)]
    if rcpt and rcpt.exists():cmd += ["--artifact",str(rcpt)]
    run(cmd,deploy,180)

def once(deploy,root,remote,pub=True):
    commit=ensure_clone(deploy,remote); q=load_json(deploy/QUEUE_REL); validate_queue(q); receipts=root/"receipts"; receipts.mkdir(parents=True,exist_ok=True); hf=root/"orchestrator_health.json"; hist=root/"history.jsonl"; enabled=[j for j in q.get("jobs",[]) if j.get("enabled")]; selected=None; waits=[]
    for j in sorted(enabled,key=lambda x:(int(x.get("priority",100)),x["id"])):
        if receipt(receipts,j).exists():continue
        bad=[]
        for d in j.get("requires",[]):
            ok,why=dep_ok(d,deploy,receipts)
            if not ok:bad.append(why)
        if not bad:selected=j;break
        waits.append(f"{j['id']}: {'; '.join(bad)}")
    if not selected:
        st="WAITING" if enabled else "IDLE"; summary="No executable job. "+(" | ".join(waits[:4]) if waits else "queue empty")
        atomic_json(hf,{"schema":1,"version":VERSION,"status":st,"updated_at_utc":now(),"pid":os.getpid(),"main_commit":commit,"queue_generation":q.get("generation"),"wait_reasons":waits,"protected_2026":not q.get("human_approved_2026",False)})
        return st,summary
    j=selected; atomic_json(hf,{"schema":1,"version":VERSION,"status":"RUNNING","updated_at_utc":now(),"pid":os.getpid(),"main_commit":commit,"queue_generation":q.get("generation"),"active_job":{"id":j["id"],"revision":j["revision"]},"protected_2026":not q.get("human_approved_2026",False)})
    if pub:publish(deploy,hf,None,"RUNNING",f"Autonomous research running {j['id']} r{j['revision']} from {commit[:10]}")
    started=now(); r=execute(j,deploy,root,hist); ro={"schema":1,"orchestrator_version":VERSION,"job_id":j["id"],"revision":j["revision"],"class_key":j.get("class_key",j["id"]),"main_commit":commit,"started_at_utc":started,"finished_at_utc":now(),"status":r.status,"exit_code":r.exit_code,"duration_seconds":r.duration,"adaptive_hard_limit_seconds":r.limit,"reason":r.reason,"stdout_tail":r.out,"stderr_tail":r.err,"protected_2026_untouched":not q.get("human_approved_2026",False)}; rp=receipt(receipts,j); atomic_json(rp,ro); append_hist(hist,{k:ro[k] for k in ("job_id","revision","class_key","status","duration_seconds","finished_at_utc")}); atomic_json(hf,{"schema":1,"version":VERSION,"status":r.status,"updated_at_utc":now(),"pid":os.getpid(),"main_commit":commit,"last_receipt":str(rp),"last_reason":r.reason})
    if pub:publish(deploy,hf,rp,r.status,f"Autonomous research {j['id']} r{j['revision']} -> {r.status}: {r.reason}")
    return r.status,r.reason

def lock(root):
    root.mkdir(parents=True,exist_ok=True); p=root/"orchestrator.lock"
    try: fd=os.open(str(p),os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.write(fd,f"{os.getpid()}\n".encode()); os.close(fd); return p
    except FileExistsError:
        try: pid=int(p.read_text().strip()); os.kill(pid,0); raise RuntimeError(f"already running pid={pid}")
        except ProcessLookupError: p.unlink(missing_ok=True); return lock(root)
        except (ValueError,PermissionError,OSError): raise RuntimeError("lock exists and is not provably stale")
def daemon(deploy,root,remote,poll):
    l=lock(root)
    try:
        while True:
            try: st,_=once(deploy,root,remote,True); time.sleep(5 if st in {"PASS","FAIL","TIMEOUT","BLOCKED"} else poll)
            except Exception as e: atomic_json(root/"orchestrator_health.json",{"schema":1,"version":VERSION,"status":"ORCHESTRATOR_ERROR","updated_at_utc":now(),"pid":os.getpid(),"error":repr(e)}); time.sleep(min(max(poll,30),300))
    finally:l.unlink(missing_ok=True)

percentile95=p95
adaptive_hard_limit=hard_limit
normalize_rel_path=relpath
dependency_satisfied=dep_ok
execute_job=execute

def main():
    a=argparse.ArgumentParser(); a.add_argument("--root",default=DEFAULT_ROOT); a.add_argument("--deploy",default=DEFAULT_DEPLOY); a.add_argument("--remote",default=DEFAULT_REMOTE); a.add_argument("--poll-seconds",type=int,default=60); a.add_argument("--once",action="store_true"); a.add_argument("--no-publish",action="store_true"); x=a.parse_args(); root=Path(x.root); deploy=Path(x.deploy)
    if x.once:
        st,why=once(deploy,root,x.remote,not x.no_publish); print(json.dumps({"status":st,"reason":why},indent=2)); return 1 if st in {"FAIL","TIMEOUT"} else 0
    return daemon(deploy,root,x.remote,x.poll_seconds)
if __name__=="__main__":raise SystemExit(main())
