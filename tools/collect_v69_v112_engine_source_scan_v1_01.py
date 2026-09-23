import os, re, csv, zipfile, hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(r"D:\MT5_Backtests")
DESKTOP = Path.home() / "Desktop"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "Research" / "ExecutionAudit" / f"V69_V112_ENGINE_SOURCE_SCAN_{STAMP}"
ZIP = DESKTOP / f"GUARDIAN_V69_V112_ENGINE_SOURCE_SCAN_{STAMP}.zip"

OUT.mkdir(parents=True, exist_ok=True)
FILES = OUT / "files_flat"
FILES.mkdir(parents=True, exist_ok=True)

# Source/config/docs only. Never inspect market-data formats.
EXTS = {".py",".ps1",".cmd",".bat",".md",".txt",".json",".yaml",".yml",".toml",".ini",".mq5",".mqh"}
MAX_BYTES = 5 * 1024 * 1024

NAME_PATTERNS = [
    "v66","v67","v68","v69","v110","v111","v112",
    "edge_factory","calendar","weekday","locked_oos","preoos","forensic"
]
CONTENT_PATTERNS = [
    "V69","GEF69","guardian_edge_factory_v69","LOCKED_OOS_RESULTS",
    "weekday","bucket","gross_bp","remove_best5",
    "V110","V111","V112","GEF110","GEF111","GEF112",
    "FROZEN_OOS_CANDIDATES","calendar_timezone","top-of-hour",
    "shift_minus5m","bootstrap_month_q025","structural_family_key",
    "weekday_idx","weekday_num","dayofweek","dt.weekday","day_name",
    "horizon_min","orientation","target_market"
]
rx = re.compile("|".join(re.escape(x) for x in CONTENT_PATTERNS), re.I)

SKIP_DIR_PARTS = {
    ".git","__pycache__",".venv","venv","node_modules",
    "executionaudit","workers"
}

hits=[]
errors=[]

def should_skip_dir(p):
    low={x.lower() for x in p.parts}
    return any(s in low for s in SKIP_DIR_PARTS)

def safe_name(name):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', name)[:100]

counter=0
for base, dirs, files in os.walk(ROOT):
    bp=Path(base)
    dirs[:] = [d for d in dirs if not should_skip_dir(bp/d)]

    for fn in files:
        p=bp/fn
        if p.suffix.lower() not in EXTS:
            continue

        try:
            size=p.stat().st_size
        except OSError as e:
            errors.append(f"STAT_ERROR {p}: {e}")
            continue
        if size > MAX_BYTES:
            continue

        try:
            raw=p.read_bytes()
        except Exception as e:
            errors.append(f"READ_ERROR {p}: {e}")
            continue

        digest=hashlib.sha256(raw).hexdigest()
        text=raw.decode("utf-8", errors="replace")

        name_hit=any(tok in fn.lower() for tok in NAME_PATTERNS)
        matched=[]
        for i,line in enumerate(text.splitlines(),1):
            if rx.search(line):
                if len(matched) < 120:
                    matched.append(f"{i}: {line[:1500]}")
        content_hit=bool(matched)

        if not (name_hit or content_hit):
            continue

        counter += 1
        flat_name=f"{counter:04d}_{digest[:12]}_{safe_name(p.name)}"
        dest=FILES/flat_name

        try:
            # Flat destination avoids Windows MAX_PATH failures from reproducing deep source trees.
            dest.write_bytes(raw)
            copy_status="OK"
        except Exception as e:
            copy_status=f"WRITE_ERROR:{e}"
            errors.append(f"WRITE_ERROR {p} -> {dest}: {e}")

        try:
            rel=str(p.relative_to(ROOT))
        except Exception:
            rel=str(p)

        hits.append({
            "flat_file":flat_name,
            "source_path":str(p),
            "relative_path":rel,
            "bytes":size,
            "sha256":digest,
            "name_hit":name_hit,
            "content_hit":content_hit,
            "copy_status":copy_status,
            "matches":"\n".join(matched),
        })

fields=["flat_file","source_path","relative_path","bytes","sha256","name_hit","content_hit","copy_status","matches"]
with open(OUT/"SOURCE_HITS.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields)
    w.writeheader()
    w.writerows(hits)

# A compact path/excerpt file is easier to inspect than the CSV alone.
with open(OUT/"MATCH_EXCERPTS.txt","w",encoding="utf-8") as f:
    for h in hits:
        f.write("="*100+"\n")
        f.write(f"FLAT_FILE: {h['flat_file']}\n")
        f.write(f"SOURCE: {h['source_path']}\n")
        f.write(f"SHA256: {h['sha256']}\n")
        f.write(h["matches"]+"\n\n")

(OUT/"ERRORS.txt").write_text("\n".join(errors),encoding="utf-8")
(OUT/"README.txt").write_text(
    "Guardian V69/V112 engine source scan v1.01\n"
    "Scans text source/config/docs only. It does NOT open parquet, market CSV, tick databases, or MT5 history.\n"
    "Matched files are stored in files_flat/ with short names to avoid Windows path-length failures.\n"
    "SOURCE_HITS.csv maps each flat file back to its exact original path and SHA256.\n"
    "Goal: recover exact engine definitions and source-data path/semantics for V69 and V110-V112.\n"
    f"Files matched: {len(hits)}\n"
    f"Errors skipped: {len(errors)}\n",
    encoding="utf-8"
)

if ZIP.exists():
    ZIP.unlink()
with zipfile.ZipFile(ZIP,"w",zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob("*"):
        if p.is_file():
            z.write(p,p.relative_to(OUT))

print("=== ENGINE SOURCE SCAN v1.01 COMPLETE ===")
print("Matches:",len(hits))
print("Skipped errors:",len(errors))
for h in hits[:30]:
    print(h["source_path"])
if len(hits)>30:
    print(f"... +{len(hits)-30} more")
print("ZIP:",ZIP)
