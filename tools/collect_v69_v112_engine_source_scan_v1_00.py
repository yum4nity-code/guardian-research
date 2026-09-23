import os, re, csv, shutil, zipfile, hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(r"D:\MT5_Backtests")
DESKTOP = Path.home() / "Desktop"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "Research" / "ExecutionAudit" / f"V69_V112_ENGINE_SOURCE_SCAN_{STAMP}"
ZIP = DESKTOP / f"GUARDIAN_V69_V112_ENGINE_SOURCE_SCAN_{STAMP}.zip"

OUT.mkdir(parents=True, exist_ok=True)
FILES = OUT / "files"
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
]
rx = re.compile("|".join(re.escape(x) for x in CONTENT_PATTERNS), re.I)

# Avoid generated result trees and virtual env/cache noise. We are after engines/source.
SKIP_DIR_PARTS = {
    ".git","__pycache__",".venv","venv","node_modules",
    "executionaudit","workers"
}

hits=[]
errors=[]

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def should_skip_dir(p):
    low={x.lower() for x in p.parts}
    return any(s in low for s in SKIP_DIR_PARTS)

for base, dirs, files in os.walk(ROOT):
    bp=Path(base)
    # prune noisy dirs but DO NOT prune Research/Autonomous wholesale; source can live there.
    dirs[:] = [d for d in dirs if not should_skip_dir(bp/d)]
    for fn in files:
        p=bp/fn
        if p.suffix.lower() not in EXTS:
            continue
        try:
            size=p.stat().st_size
        except OSError:
            continue
        if size > MAX_BYTES:
            continue

        name_hit=any(tok in fn.lower() for tok in NAME_PATTERNS)
        content_hit=False
        matched=[]
        try:
            text=p.read_text(encoding="utf-8",errors="replace")
            for i,line in enumerate(text.splitlines(),1):
                if rx.search(line):
                    content_hit=True
                    if len(matched) < 80:
                        matched.append(f"{i}: {line[:1200]}")
        except Exception as e:
            errors.append(f"{p}: {e}")
            continue

        if not (name_hit or content_hit):
            continue

        # Prefer files that are plausibly code/engine/config. Markdown is retained if it reveals paths/semantics.
        rel=p.relative_to(ROOT)
        dest=FILES/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest)
        hits.append({
            "path":str(p),
            "relative_path":str(rel),
            "bytes":size,
            "sha256":sha256(p),
            "name_hit":name_hit,
            "content_hit":content_hit,
            "matches":"\n".join(matched),
        })

with open(OUT/"SOURCE_HITS.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["path","relative_path","bytes","sha256","name_hit","content_hit","matches"])
    w.writeheader()
    w.writerows(hits)

(OUT/"ERRORS.txt").write_text("\n".join(errors),encoding="utf-8")
(OUT/"README.txt").write_text(
    "Guardian V69/V112 engine source scan\n"
    "Scans text source/config/docs only. It does NOT open parquet, market CSV, tick databases, or MT5 history.\n"
    "Goal: recover the exact engine definitions and source-data path/semantics for V69 and V110-V112.\n"
    f"Files matched: {len(hits)}\n",
    encoding="utf-8"
)

if ZIP.exists():
    ZIP.unlink()
with zipfile.ZipFile(ZIP,"w",zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob("*"):
        if p.is_file():
            z.write(p,p.relative_to(OUT))

print("=== ENGINE SOURCE SCAN COMPLETE ===")
print("Matches:",len(hits))
for h in hits[:40]:
    print(h["path"])
if len(hits)>40:
    print(f"... +{len(hits)-40} more")
print("ZIP:",ZIP)
