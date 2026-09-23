from __future__ import annotations
from pathlib import Path
import argparse, csv, hashlib, json, math, re, shutil, sys, zipfile
from collections import defaultdict
import pandas as pd
import numpy as np

VERSION="GUARDIAN-MINI-EDGE-EXTRACTOR-1.1"

TEXT_EXT={".json",".csv",".md",".txt",".log"}
RESULT_NAME_RE=re.compile(r"(result|results|summary|verdict|receipt|decision|validation|replication|holdout|oos|out[-_ ]?of[-_ ]?sample|score|metric|stats|audit|report)",re.I)
METRIC_NAME_RE=re.compile(r"(mean|avg|average|ev|expect|edge|profit|pnl|net_r|gross_r|pf|profit_factor|p[_ -]?(one|value)?|sharpe|sortino|win|hit|trades|episodes|days|count|(^|_)n($|_)|drawdown|dd|return|bps|r_trade|r\/trade)",re.I)
STATUS_RE=re.compile(r"(reject|fail|failed|close|closed|watchlist|do_not_advance|not_confirmed|unconfirmed|pass|validated|confirmed|survivor)",re.I)
POSITIVE_HINT_RE=re.compile(r"(mean|ev|edge|pnl|profit|return|bps|net_r|gross_r)",re.I)

MAX_COPY_MB=30
MAX_CSV_MB=80
MAX_TEXT_MB=20
MAX_ROWS_PER_CSV=250000

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""): h.update(ch)
    return h.hexdigest()

def safe_rel(p:Path, roots):
    for label,root in roots:
        try:
            return label+"/"+str(p.relative_to(root)).replace("\\","/")
        except Exception:
            pass
    return str(p).replace("\\","/").replace(":","")

def is_candidate_file(p:Path):
    if p.suffix.lower() not in TEXT_EXT: return False
    s=str(p).lower()
    if RESULT_NAME_RE.search(p.name): return True
    if any(x in s for x in ["research\\autonomous","research/autonomous","research\\results","research/results","backtests\\inbox","backtests/inbox"]):
        return p.suffix.lower() in {".json",".csv",".md"}
    return False

def flatten_json(x,prefix=""):
    out={}
    if isinstance(x,dict):
        for k,v in x.items():
            key=f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v,(dict,list)):
                out.update(flatten_json(v,key))
            else:
                out[key]=v
    elif isinstance(x,list):
        for i,v in enumerate(x[:500]):
            key=f"{prefix}[{i}]"
            if isinstance(v,(dict,list)): out.update(flatten_json(v,key))
            else: out[key]=v
    return out

def num(v):
    if isinstance(v,(int,float,np.integer,np.floating)) and not isinstance(v,bool):
        return float(v) if math.isfinite(float(v)) else None
    if isinstance(v,str):
        s=v.strip().replace(",","")
        try:
            z=float(s)
            return z if math.isfinite(z) else None
        except: return None
    return None

def status_text_from_mapping(m):
    vals=[]
    for k,v in m.items():
        if isinstance(v,(str,bool,int,float)) and re.search(r"(status|verdict|decision|pass|fail|result|next)",str(k),re.I):
            vals.append(f"{k}={v}")
    return " | ".join(vals)[:3000]

def inspect_json(p,source):
    rows=[]; candidates=[]
    try:
        obj=json.loads(p.read_text(encoding="utf-8",errors="replace"))
    except Exception:
        return rows,candidates
    flat=flatten_json(obj)
    status=status_text_from_mapping(flat)
    metrics={}
    for k,v in flat.items():
        nv=num(v)
        if nv is not None and METRIC_NAME_RE.search(k):
            metrics[k]=nv
            rows.append({"source":source,"format":"json","record":"","metric":k,"value":nv,"status":status})
    rejected=bool(STATUS_RE.search(status) and re.search(r"(reject|fail|closed|close|do_not_advance|not_confirmed|unconfirmed)",status,re.I))
    positive=[(k,v) for k,v in metrics.items() if POSITIVE_HINT_RE.search(k) and v>0]
    if rejected and positive:
        candidates.append({"source":source,"record":"","status":status,"positive_metrics":"; ".join(f"{k}={v:.8g}" for k,v in positive[:20]),"reason":"rejected/status-negative while one or more effect metrics are positive"})
    return rows,candidates

def inspect_csv(p,source):
    """
    Fast audit path:
    - read header first;
    - skip large raw trade ledgers that have no verdict/status column;
    - for verdict-style CSVs, read only useful columns in chunks;
    - vectorize rejection filtering before iterating the small rejected subset.
    """
    metrics=[]; candidates=[]
    size_mb=p.stat().st_size/1024/1024
    if size_mb>MAX_CSV_MB:
        return metrics,candidates

    sep=","
    try:
        head=pd.read_csv(p,nrows=0)
        cols=[str(c) for c in head.columns]
        if len(cols)<=1:
            head=pd.read_csv(p,nrows=0,sep=";")
            cols=[str(c) for c in head.columns]
            sep=";"
    except Exception:
        return metrics,candidates

    metric_cols=[c for c in cols if METRIC_NAME_RE.search(c)]
    status_cols=[c for c in cols if re.search(r"(status|verdict|decision|pass|fail|result)",c,re.I)]
    id_cols=[c for c in cols if re.search(r"(^id$|variant|candidate|strategy|symbol|market|family|target|name)",c,re.I)]

    if not metric_cols:
        return metrics,candidates

    # Raw trade/outcome ledgers can contain hundreds of thousands of rows and
    # positive/negative trade metrics but no decision. They do not answer the
    # audit question "positive yet rejected", so do not scan them row-by-row.
    if not status_cols and size_mb>2:
        return metrics,candidates

    usecols=[]
    for x in id_cols[:5]+status_cols[:5]+metric_cols:
        if x not in usecols:
            usecols.append(x)

    total_seen=0
    try:
        reader=pd.read_csv(
            p,sep=sep,usecols=usecols,chunksize=20000,
            low_memory=False
        )
        for chunk in reader:
            if total_seen>=MAX_ROWS_PER_CSV:
                break
            if total_seen+len(chunk)>MAX_ROWS_PER_CSV:
                chunk=chunk.iloc[:MAX_ROWS_PER_CSV-total_seen]
            base_index=total_seen
            total_seen+=len(chunk)
            if chunk.empty:
                continue

            if status_cols:
                s=chunk[status_cols[:5]].fillna("").astype(str).agg(" | ".join,axis=1)
                rejected_mask=s.str.contains(
                    r"(false|reject|fail|closed|close|do_not_advance|not_confirmed|unconfirmed)",
                    case=False,regex=True,na=False
                )
            else:
                s=pd.Series("",index=chunk.index)
                rejected_mask=pd.Series(False,index=chunk.index)

            # Keep metric observations from small summary tables. For larger
            # verdict tables, rejected rows are the audit-relevant population.
            rows_for_metrics = chunk.index if total_seen<=50000 else chunk.index[rejected_mask]

            for c in metric_cols:
                vals=pd.to_numeric(chunk.loc[rows_for_metrics,c],errors="coerce")
                good=vals.notna() & np.isfinite(vals)
                for idx,v in vals[good].items():
                    rec=" | ".join(
                        f"{ic}={chunk.at[idx,ic]}" for ic in id_cols[:5]
                        if ic in chunk.columns and pd.notna(chunk.at[idx,ic])
                    )[:1000]
                    metrics.append({
                        "source":source,"format":"csv",
                        "record":rec or str(base_index+int(idx)),
                        "metric":c,"value":float(v),
                        "status":str(s.loc[idx])[:2000]
                    })

            if rejected_mask.any():
                rej=chunk.loc[rejected_mask]
                for idx,row in rej.iterrows():
                    positives=[]
                    for mc in metric_cols:
                        nv=num(row[mc])
                        if nv is not None and POSITIVE_HINT_RE.search(mc) and nv>0:
                            positives.append((mc,nv))
                    if not positives:
                        continue
                    rec=" | ".join(
                        f"{ic}={row[ic]}" for ic in id_cols[:5]
                        if ic in rej.columns and pd.notna(row[ic])
                    )[:1000]
                    candidates.append({
                        "source":source,
                        "record":rec or str(base_index+int(idx)),
                        "status":str(s.loc[idx])[:2000],
                        "positive_metrics":"; ".join(f"{k}={v:.8g}" for k,v in positives[:20]),
                        "reason":"row rejected/status-negative while one or more effect metrics are positive"
                    })
    except Exception:
        return metrics,candidates

    return metrics,candidates

def inspect_markdown(p,source):
    metrics=[]; candidates=[]
    if p.stat().st_size/1024/1024>MAX_TEXT_MB:return metrics,candidates
    txt=p.read_text(encoding="utf-8",errors="replace")
    statuslines=[x.strip() for x in txt.splitlines() if STATUS_RE.search(x)]
    status=" | ".join(statuslines[:20])[:3000]
    # Capture simple "label: +0.123R", "= 5.2 bps", etc.
    pat=re.compile(r"(?P<label>[A-Za-z0-9_ /\-\+\.\(\)%]{2,80}?)(?:[:=]| is | about )\s*\*{0,2}(?P<val>[+-]?\d+(?:\.\d+)?)(?P<unit>\s*(?:R(?:/trade|/event)?|bps|%|USD|\$)?)",re.I)
    positives=[]
    for m in pat.finditer(txt):
        label=" ".join(m.group("label").split())[-120:]
        if not METRIC_NAME_RE.search(label): continue
        try:v=float(m.group("val"))
        except:continue
        unit=m.group("unit").strip()
        metric=(label+" "+unit).strip()
        metrics.append({"source":source,"format":"markdown","record":"","metric":metric,"value":v,"status":status})
        if POSITIVE_HINT_RE.search(label) and v>0: positives.append((metric,v))
    rejected=bool(re.search(r"(reject|fail|closed|close|do not advance|not confirmed|unconfirmed)",status,re.I))
    if rejected and positives:
        candidates.append({"source":source,"record":"","status":status,
                           "positive_metrics":"; ".join(f"{k}={v:.8g}" for k,v in positives[:20]),
                           "reason":"document has rejection language while effect metrics are positive"})
    return metrics,candidates

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"D:\MT5_Backtests")
    ap.add_argument("--output",default="")
    args=ap.parse_args()
    root=Path(args.root)
    repo=root/"guardian-research"
    roots=[]
    candidates=[
        ("Research_Autonomous",root/"Research"/"Autonomous"),
        ("Repo_Research_Results",repo/"research"/"results"),
        ("Repo_Backtests_Inbox",repo/"backtests"/"inbox"),
        ("Root_Backtests_Inbox",root/"backtests"/"inbox"),
        ("Repo_Results",repo/"results"),
    ]
    for label,p in candidates:
        if p.exists(): roots.append((label,p))
    if not roots:
        raise SystemExit("No expected Guardian result roots found.")

    stamp=pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out=Path(args.output) if args.output else root/"Research"/"Exports"/f"GUARDIAN_MINI_EDGE_AUDIT_{stamp}"
    out.mkdir(parents=True,exist_ok=False)
    artifacts=out/"artifacts";artifacts.mkdir()

    inventory=[]; metric_rows=[]; candidate_rows=[]; errors=[]
    seen=set()
    files=[]
    for label,r in roots:
        for p in r.rglob("*"):
            if not p.is_file() or not is_candidate_file(p): continue
            try:key=(p.resolve(),p.stat().st_size)
            except:key=(str(p),0)
            if key in seen:continue
            seen.add(key);files.append(p)

    print(f"[EXTRACT] candidate files: {len(files)}",flush=True)
    for n,p in enumerate(files,1):
        source=safe_rel(p,roots)
        try:
            size=p.stat().st_size
            inv={"source":source,"path":str(p),"extension":p.suffix.lower(),"bytes":size,"sha256":sha256(p),"copied":False,"notes":""}
            ext=p.suffix.lower()
            if ext==".json": m,c=inspect_json(p,source)
            elif ext==".csv": m,c=inspect_csv(p,source)
            elif ext in {".md",".txt",".log"}: m,c=inspect_markdown(p,source)
            else:m,c=[],[]
            metric_rows.extend(m);candidate_rows.extend(c)
            if size<=MAX_COPY_MB*1024*1024:
                dst=artifacts/source
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(p,dst);inv["copied"]=True
            else:
                inv["notes"]=f"not copied: >{MAX_COPY_MB} MB; metrics inspected when supported"
            inventory.append(inv)
        except Exception as e:
            errors.append({"source":source,"path":str(p),"error":repr(e)})
        if n%250==0: print(f"[EXTRACT] {n}/{len(files)}",flush=True)

    invdf=pd.DataFrame(inventory)
    metdf=pd.DataFrame(metric_rows)
    candf=pd.DataFrame(candidate_rows).drop_duplicates() if candidate_rows else pd.DataFrame(columns=["source","record","status","positive_metrics","reason"])
    errdf=pd.DataFrame(errors)

    invdf.to_csv(out/"FILE_INVENTORY.csv",index=False)
    metdf.to_csv(out/"EXTRACTED_METRICS.csv",index=False)
    candf.to_csv(out/"POSITIVE_BUT_REJECTED_CANDIDATES.csv",index=False)
    errdf.to_csv(out/"EXTRACTION_ERRORS.csv",index=False)

    # Human-readable shortlist: ranked only by source/record, NOT by performance.
    report=[
      "# GUARDIAN Mini-Edge Local Extraction",
      "",
      f"Version: {VERSION}",
      f"Generated UTC: {pd.Timestamp.now('UTC')}",
      f"Roots scanned: {len(roots)}",
      f"Candidate files inspected: {len(inventory)}",
      f"Metric observations extracted: {len(metric_rows)}",
      f"Automatically flagged positive-but-rejected rows/docs: {len(candf)}",
      f"Extraction errors: {len(errors)}",
      "",
      "## Important",
      "This extractor does not rerun any backtest and does not change any result.",
      "Automatic flags are leads for manual audit, not proof of an edge.",
      "A positive metric can refer to a diagnostic or subgroup, so every candidate must be checked against its source artifact.",
      "",
      "## Roots",
    ]
    report += [f"- {label}: {path}" for label,path in roots]
    report += ["","## Flagged candidates"]
    for _,r in candf.head(300).iterrows():
        report.append(f"- {r['source']} :: {r.get('record','')} :: {r.get('positive_metrics','')}")
    if len(candf)>300:report.append(f"- ... {len(candf)-300} more in POSITIVE_BUT_REJECTED_CANDIDATES.csv")
    (out/"README_AUDIT.md").write_text("\n".join(report),encoding="utf-8")

    receipt={
      "version":VERSION,
      "status":"COMPLETE_LOCAL_RESULT_EXTRACTION",
      "output_dir":str(out),
      "roots":[{"label":l,"path":str(p)} for l,p in roots],
      "files_inspected":len(inventory),
      "metric_observations":len(metric_rows),
      "auto_flagged_positive_but_rejected":len(candf),
      "errors":len(errors),
      "research_rerun":False,
      "market_data_modified":False
    }
    (out/"RUN_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")

    zip_path=out.with_suffix(".zip")
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,allowZip64=True) as z:
        for p in out.rglob("*"):
            if p.is_file(): z.write(p,p.relative_to(out.parent))
    print("\n=== MINI-EDGE EXTRACTION RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\nZIP:",zip_path)

if __name__=="__main__":
    main()
