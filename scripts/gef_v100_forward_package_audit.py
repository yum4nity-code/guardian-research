from pathlib import Path
import json, hashlib, os
import pandas as pd

ROOT=Path(r"D:\MT5_Backtests")
REPO=ROOT/"guardian-research"
BASE=ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v100_forward_package"
BASE.mkdir(parents=True,exist_ok=True)
ENGINE_VERSION="V100.0"

MQ5=REPO/"mt5"/"GuardianEdgeForward"/"GuardianEdgeForward.mq5"
README=REPO/"mt5"/"GuardianEdgeForward"/"README.md"
TEMPLATE=REPO/"mt5"/"GuardianEdgeForward"/"state_seed_v100_TEMPLATE.csv"

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(p,o):
    p.write_text(json.dumps(o,indent=2,default=str),encoding="utf-8")

def status(out,step,total,msg,**extra):
    payload={
        "engine_version":ENGINE_VERSION,
        "step":step,"steps":total,
        "percent":round(step/total*100,1),
        "timestamp_utc":pd.Timestamp.now("UTC").isoformat(),
        "message":msg,**extra,
    }
    write_json(out/"LIVE_STATUS.json",payload)
    tail=" | ".join(f"{k}={v}" for k,v in extra.items())
    print(f"[GEF100] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

v97e_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v97e_corrected_2026_freeze").glob("GEF97E-*"))
v97e_runs=[p for p in v97e_runs if (p/"RUN_RECEIPT.json").exists()]
if not v97e_runs:
    raise RuntimeError("No V97E")
V97E=v97e_runs[-1]
r97e=json.loads((V97E/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r97e.get("status")!="COMPLETE_V97E_CORRECTED_2026_FREEZE":
    raise RuntimeError("V97E incomplete")
if r97e.get("2026_values_accessed"):
    raise RuntimeError("V97E reports 2026 access")
if r97e.get("corrected_promoted_ranks")!=[7,9]:
    raise RuntimeError("Unexpected frozen ranks")

v99_runs=sorted((ROOT/"Research"/"Autonomous"/"guardian_edge_factory_v99_execution_reality").glob("GEF99-*"))
v99_runs=[p for p in v99_runs if (p/"RUN_RECEIPT.json").exists()]
if not v99_runs:
    raise RuntimeError("No V99")
V99=v99_runs[-1]
r99=json.loads((V99/"RUN_RECEIPT.json").read_text(encoding="utf-8"))
if r99.get("status")!="COMPLETE_V99_EXECUTION_REALITY_AUDIT":
    raise RuntimeError("V99 incomplete")
if r99.get("2026_values_requested_or_stored"):
    raise RuntimeError("V99 reports 2026 access")
if r99.get("frozen_panel_sha256")!=r97e.get("frozen_panel_sha256"):
    raise RuntimeError("V99/V97E hash mismatch")

for p in (MQ5,README,TEMPLATE):
    if not p.exists():
        raise RuntimeError(f"Missing package file {p}")

RID="GEF100-"+pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
OUT=BASE/RID
OUT.mkdir(parents=True,exist_ok=False)
status(OUT,1,7,"V97E/V99 lineage verified; no 2026 market file opened",source_v97e=V97E.name,source_v99=V99.name)

src=MQ5.read_text(encoding="utf-8")
required_literals=[
    "#define ACTIVATION_NOT_BEFORE D'2027.01.01 00:00'",
    'const string SYM_DXY="DXY.cash";',
    'const string SYM_USDJPY="USDJPY";',
    'const string SYM_USDCHF="USDCHF";',
    'const string SYM_XAUUSD="XAUUSD";',
    'const string SYM_GBPUSD="GBPUSD";',
    "WriteSignal(7",
    "WriteSignal(9",
    "a.lo && b.hi",
    "a.hi && b.hi",
]
missing=[x for x in required_literals if x not in src]
if missing:
    raise RuntimeError(f"V100 source contract missing {missing}")

for forbidden in ("OrderSend(","CTrade","PositionOpen(","trade.Buy(","trade.Sell("):
    if forbidden in src:
        raise RuntimeError(f"Shadow-only contract violated by {forbidden}")

if "return INIT_FAILED;" not in src or "TimeCurrent()<ACTIVATION_NOT_BEFORE" not in src:
    raise RuntimeError("Hard activation lock missing")

status(OUT,2,7,"MQL5 static contract verified",shadow_only=True,activation_not_before="2027-01-01")

contracts={
    "7":{
        "feature_a":"price_USDJPY_zret_60m","state_a":"LO",
        "feature_b":"price_USDCHF_rv_60m","state_b":"HI",
        "target":"DXY.cash","direction":"LONG","horizon_min":15,
    },
    "9":{
        "feature_a":"price_XAUUSD_rv_60m","state_a":"HI",
        "feature_b":"price_GBPUSD_ret_30m","state_b":"HI",
        "target":"GBPUSD","direction":"SHORT","horizon_min":30,
    },
}
write_json(OUT/"FROZEN_FORWARD_CONTRACT.json",contracts)
status(OUT,3,7,"rank 7/9 forward contract frozen in deployment receipt")

template=TEMPLATE.read_text(encoding="utf-8")
if template.count("REPLACE_AFTER_2026")!=12:
    raise RuntimeError("Seed template no longer visibly protected")
status(OUT,4,7,"post-2026 seed requirement verified; no usable seed shipped")

compile_log=os.environ.get("GEF100_COMPILE_LOG","").strip()
compile_status="NOT_ATTEMPTED"
compile_tail=None
if compile_log and Path(compile_log).exists():
    raw=Path(compile_log).read_bytes()
    txt=""
    for enc in ("utf-16","utf-8","cp1252"):
        try:
            txt=raw.decode(enc)
            if txt.strip():
                break
        except Exception:
            pass
    compile_tail=txt[-3000:]
    low=txt.lower()
    if "0 errors" in low:
        compile_status="PASS"
    elif "error" in low:
        compile_status="FAIL"
        raise RuntimeError(f"MetaEditor compile failed; see {compile_log}")
    else:
        compile_status="UNKNOWN"
status(OUT,5,7,"compile evidence inspected",compile_status=compile_status)

manifest={
    "run_id":RID,
    "status":"V100_FORWARD_SHADOW_PACKAGE_FROZEN",
    "source_v97e":V97E.name,
    "source_v99":V99.name,
    "frozen_panel_sha256":r97e["frozen_panel_sha256"],
    "frozen_ranks":[7,9],
    "mq5_path":str(MQ5),
    "mq5_sha256":sha256(MQ5),
    "readme_sha256":sha256(README),
    "seed_template_sha256":sha256(TEMPLATE),
    "compile_status":compile_status,
    "compile_log_tail":compile_tail,
    "activation_not_before":"2027-01-01 00:00",
    "shadow_only":True,
    "real_seed_included":False,
    "order_sending_code_present":False,
    "2026_market_values_accessed":False,
    "next":"AFTER FULL 2026 OOS RELEASE: SCORE FROZEN RANKS 7/9, GENERATE EXACT FTMO-CONTINUATION STATE SEED, THEN START FORWARD SHADOW; DO NOT ACTIVATE BEFORE RELEASE",
}
write_json(OUT/"DEPLOYMENT_MANIFEST.json",manifest)
status(OUT,6,7,"deployment manifest frozen",mq5_sha256=manifest["mq5_sha256"][:16])
write_json(OUT/"RUN_RECEIPT.json",manifest)
status(OUT,7,7,"DONE; package audited without opening 2026")

print("\n=== V100 RECEIPT ===")
print(json.dumps(manifest,indent=2))
print("\nRUN:",OUT)
