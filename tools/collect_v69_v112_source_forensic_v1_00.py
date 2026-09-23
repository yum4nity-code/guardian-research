import csv, os, re, shutil, sys, zipfile, hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(r"D:\MT5_Backtests")
AUTO = ROOT / "Research" / "Autonomous"
DESKTOP = Path.home() / "Desktop"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "Research" / "ExecutionAudit" / f"V69_V112_SOURCE_FORENSIC_{STAMP}"
ZIP = DESKTOP / f"GUARDIAN_V69_V112_SOURCE_FORENSIC_{STAMP}.zip"

TARGET_DIR_TOKENS = [
    "guardian_edge_factory_v66",
    "guardian_edge_factory_v67",
    "guardian_edge_factory_v68",
    "guardian_edge_factory_v69",
    "guardian_edge_factory_v110",
    "guardian_edge_factory_v111",
    "guardian_edge_factory_v112",
]

TEXT_EXTS = {".py",".ps1",".md",".json",".txt",".csv",".cmd",".mq5",".mqh",".set",".ini",".yaml",".yml",".toml"}
MAX_TEXT_BYTES = 10 * 1024 * 1024
CSV_NAME_HINTS = (
    "candidate","result","receipt","gate","forensic","eligible","survivor",
    "frozen","report","summary","manifest","config","decision"
)
TERMS = [
    "weekday","bucket","hour_utc","hour","horizon","orientation","utc",
    "copy_rates","resample","read_csv","read_parquet","source","market",
    "eligible","2023","2025","2026","locked_oos","v69","v112",
    "usdchf","audusd","close","open","shift_plus5","shift_minus5"
]

OUT.mkdir(parents=True, exist_ok=True)
copy_root = OUT / "files"
copy_root.mkdir(parents=True, exist_ok=True)

inventory=[]
excerpts=[]

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def allowed(p):
    if not p.is_file():
        return False
    ext=p.suffix.lower()
    if ext not in TEXT_EXTS:
        return False
    try:
        sz=p.stat().st_size
    except OSError:
        return False
    if sz > MAX_TEXT_BYTES:
        return False
    if ext==".csv":
        n=p.name.lower()
        return any(h in n for h in CSV_NAME_HINTS)
    return True

targets=[]
if AUTO.exists():
    for child in AUTO.iterdir():
        if child.is_dir() and any(tok in child.name.lower() for tok in TARGET_DIR_TOKENS):
            targets.append(child)

# Also catch nested or oddly named matching directories.
for base, dirs, files in os.walk(AUTO if AUTO.exists() else ROOT):
    b=Path(base)
    low=str(b).lower()
    if any(tok in low for tok in TARGET_DIR_TOKENS):
        if b not in targets:
            targets.append(b)
        dirs[:] = []  # parent match will be recursively handled below

# De-duplicate and keep highest-level matches.
uniq=[]
for p in sorted(set(targets), key=lambda x: (len(x.parts), str(x))):
    if not any(parent in p.parents for parent in uniq):
        uniq.append(p)
targets=uniq

for td in targets:
    for p in td.rglob("*"):
        if not allowed(p):
            continue
        try:
            rel=p.relative_to(ROOT)
        except Exception:
            rel=Path(p.name)
        dest=copy_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(p,dest)
            digest=sha256(p)
            sz=p.stat().st_size
            inventory.append({
                "source_path":str(p),
                "relative_path":str(rel),
                "bytes":sz,
                "sha256":digest,
            })
            try:
                txt=p.read_text(encoding="utf-8",errors="replace")
                for i,line in enumerate(txt.splitlines(),1):
                    ll=line.lower()
                    if any(t in ll for t in TERMS):
                        excerpts.append(f"{p}:{i}: {line[:1000]}")
            except Exception as e:
                excerpts.append(f"READ_ERROR {p}: {e}")
        except Exception as e:
            inventory.append({
                "source_path":str(p),
                "relative_path":str(rel),
                "bytes":"",
                "sha256":f"COPY_ERROR:{e}",
            })

# Add exact known run artifacts if present, but no broad market-data files.
known_patterns = [
    r"Research\Autonomous\guardian_edge_factory_v69*\**\OOS_GATE_PREDECLARED.json",
    r"Research\Autonomous\guardian_edge_factory_v69*\**\RUN_RECEIPT.json",
    r"Research\Autonomous\guardian_edge_factory_v111*\**\FORENSIC_RESULTS.csv",
    r"Research\Autonomous\guardian_edge_factory_v111*\**\V111_REPORT.md",
    r"Research\Autonomous\guardian_edge_factory_v112*\**\RUN_RECEIPT.json",
]
for pat in known_patterns:
    for p in ROOT.glob(pat):
        if not p.is_file():
            continue
        rel=p.relative_to(ROOT)
        dest=copy_root/rel
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,dest)

with open(OUT/"FORENSIC_INVENTORY.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["source_path","relative_path","bytes","sha256"])
    w.writeheader()
    w.writerows(inventory)

(OUT/"MATCH_EXCERPTS.txt").write_text("\n".join(excerpts),encoding="utf-8")
(OUT/"README.txt").write_text(
    "GUARDIAN V69/V112 SOURCE FORENSIC COLLECTOR\n"
    "Purpose: collect source code and small metadata needed to reproduce original gross-event semantics.\n"
    "No MT5 queries are made. No market-data parquet/tick/history files are copied.\n"
    "Protected 2026 market data is not opened by this collector.\n"
    f"Target roots found: {len(targets)}\n"
    f"Files collected: {len(inventory)}\n",
    encoding="utf-8"
)

if ZIP.exists():
    ZIP.unlink()
with zipfile.ZipFile(ZIP,"w",zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob("*"):
        if p.is_file():
            z.write(p,p.relative_to(OUT))

print("=== SOURCE FORENSIC COMPLETE ===")
print(f"Target roots: {len(targets)}")
for t in targets:
    print("ROOT:",t)
print(f"Files collected: {len(inventory)}")
print(f"ZIP: {ZIP}")
