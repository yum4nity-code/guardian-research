#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,os,shutil,subprocess,sys,time
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
VERSION="1.00"
DEFAULT_REMOTE="git@github.com:yum4nity-code/guardian-research.git"
DEFAULT_DEPLOY=r"D:\MT5_Backtests\guardian-autonomous-main"
DEFAULT_ROOT=r"D:\MT5_Backtests\Research\Autonomous"
QUEUE_REL=Path("research/autonomous/RESEARCH_QUEUE.json")
QUEUE_APPEND_REL=Path("research/autonomous/RESEARCH_QUEUE_APPEND.json")
PUBLISHER_REL=Path("research/phenomenon_discovery/publish_phase_result_v1_00.py")
PROTECTED_2026_EPOCH=datetime(2026,1,1,tzinfo=timezone.utc)

def now():return datetime.now(timezone.utc).isoformat()
def load_json(p):return json.loads(p.read_text(encoding="utf-8"))
def atomic_json(p,o):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(o,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(t,p)
def run(cmd,cwd,timeout=120):return subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=timeout,check=False)
def git(deploy,*args,timeout=120):
 cp=run(["git",*args],deploy,timeout)
 if cp.returncode:raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip() or cp.stdout.strip()}")
 return cp.stdout.strip()
def ensure_clone(deploy,remote):
 if not (deploy/".git").exists():
  deploy.parent.mkdir(parents=True,exist_ok=True); cp=run(["git","clone",remote,str(deploy)],deploy.parent,300)
  if cp.returncode:raise RuntimeError(cp.stderr.strip() or cp.stdout.strip())
 git(deploy,"fetch","origin","main","backtest-results",timeout=300); git(deploy,"checkout","-B","main","origin/main"); git(deploy,"reset","--hard","origin/main"); return git(deploy,"rev-parse","HEAD")
def parse_dt(s):
 x=datetime.fromisoformat(s.replace("Z","+00:00")); return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
def relpath(x):
 p=Path(x)
 if p.is_absolute() or ".." in p.parts:raise ValueError(f"unsafe path {x}")
 return p
def load_queue(deploy):
 q=load_json(deploy/QUEUE_REL)
 ap=deploy/QUEUE_APPEND_REL
 if ap.exists():
  extra=load_json(ap)
  if extra.get("schema")!=1 or not isinstance(extra.get("jobs"),list):raise ValueError("invalid queue append schema")
  q["jobs"]=[*q.get("jobs",[]),*extra["jobs"]]
  q["generation"]=max(int(q.get("generation",0)),int(extra.get("generation",0)))
 return q
def validate_queue(q):
 if q.get("schema")!=1:raise ValueError("queue schema")
 allow=bool(q.get("human_approved_2026",False)); seen=set()
 for j in q.get("jobs",[]):
  key=(j["id"],int(j["revision"]));
  if key in seen:raise ValueError(f"duplicate {key}")
  seen.add(key); relpath(j.get("executor",{}).get("path","x")) if j.get("executor",{}).get("kind") not in {"noop","codex_assist"} else None
  w=j.get("data_window")
  if w and parse_dt(w["end_exclusive"])>PROTECTED_2026_EPOCH and not allow:raise ValueError(f"protected 2026 blocked: {key}")
def dep_ok(d,deploy,receipts):
 k=d["kind"]
 if k=="receipt":
  p=receipts/f"{d['job_id']}__r{d['revision']}.json"
  if not p.exists():return False,f"missing {p.name}"
  s=load_json(p).get("status"); ok=s in d.get("accepted_status",["PASS"]); return ok,f"{p.name} status {s}"
 if k=="github_result":
  ref=d.get("ref","origin/backtest-results"); cp=run(["git","show",f"{ref}:{d['path']}"],deploy,60)
  if cp.returncode:return False,f"missing {d['path']} on {ref}"
  try:s=json.loads(cp.stdout).get("status")
  except Exception:return False,f"invalid json {d['path']}"
  return s in d.get("accepted_status",["PASS"]),f"{d['path']} status {s}"
 return False,f"unknown dependency {k}"
def expand(s,root,deploy,jid):return s.replace("{ROOT}",str(root)).replace("{DEPLOY}",str(deploy)).replace("{JOB_ID}",jid)
def p95(v):
 if not v:return None
 a=sorted(v); i=.95*(len(a)-1); lo=int(math.floor(i)); hi=int(math.ceil(i)); return a[lo] if lo==hi else a[lo]+(a[hi]-a[lo])*(i-lo)
def history(p,key):
 if not p.exists():return []
 z=[]
 for l in p.read_text(encoding="utf-8",errors="replace").splitlines():
  try:o=json.loads(l)
  except:continue
  if o.get("class_key")==key and o.get("status")=="PASS" and isinstance(o.get("duration_seconds"),(int,float)):z.append(float(o["duration_seconds"]))
 return z
def hard_limit(pol,hist,elapsed=0,frac=None):
 vals=[float(pol.get("min_seconds",60)),float(pol.get("expected_seconds",60))*float(pol.get("eta_multiplier",2.5))]
 h=p95(hist)
 if h:vals.append(h*float(pol.get("history_p95_multiplier",3)))
 if frac and frac>0 and elapsed>0:vals.append((elapsed/frac)*float(pol.get("eta_multiplier",2.5)))
 return max(vals)
def progress(p):
 if not p or not p.exists():return None,None
 mt=p.stat().st_mtime
 try:
  o=load_json(p); f=o.get("fraction")
  if f is None and o.get("completed") is not None and o.get("total"):f=float(o["completed"])/float(o["total"])
  return (float(f) if f is not None else None),mt
 except:return None,mt
def kill_tree(p):
 if os.name=="nt":subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True)
 else:
  try:os.killpg(p.pid,15);time.sleep(2);os.killpg(p.pid,9)
  except:pass
@dataclass
class Result:status:str;exit_code:int|None;duration:float;reason:str;out:str;err:str;limit:float
def execute(job,deploy,root,histfile):
 ex=job["executor"];kind=ex["kind"]
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
 commit=ensure_clone(deploy,remote); q=load_queue(deploy); validate_queue(q); receipts=root/"receipts"; receipts.mkdir(parents=True,exist_ok=True); hf=root/"orchestrator_health.json"; hist=root/"history.jsonl"; enabled=[j for j in q.get("jobs",[]) if j.get("enabled")]; selected=None; waits=[]
 for j in sorted(enabled,key=lambda x:(int(x.get("priority",100)),x["id"],int(x.get("revision",0)))):
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
