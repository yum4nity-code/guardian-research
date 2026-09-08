#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json, math
from pathlib import Path

STEP_MS=300000
HORIZONS={"15m":3,"30m":6,"1h":12,"2h":24,"4h":48}
SHOCKS=[
"oi_change_15m_pct","oi_change_1h_pct","oi_accel_15m_pctpt","atr_slope_3bar_pct","range_atr",
"mark_index_bps_change_15m","mark_index_bps_change_1h","premium_index_change_15m","premium_index_change_1h",
"taker_imbalance_diff_change_15m","taker_imbalance_diff_change_1h","spot_taker_imbalance_change_15m","perp_taker_imbalance_change_15m",
"perp_spot_basis_bps_change_15m","perp_spot_basis_bps_change_1h","spot_volume_shock_1h","perp_volume_shock_1h","spot_trade_shock_1h","perp_trade_shock_1h"]

def finite(x):
    if x in (None,""): return False
    try: return math.isfinite(float(x))
    except (TypeError,ValueError): return False

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\event_shock_v1"); a=ap.parse_args(); root=Path(a.input_dir)
    report={"schema":1,"phase":"H-A","status":"PASS","protected_2026_untouched":True,"cross_year_future_labels_forbidden":True,"news_mask_applied":False,"propfirm_tradability_authorized":False,"symbols":{}}
    failures=[]
    for sym in ("BTCUSDT","ETHUSDT"):
        p=root/f"{sym}_event_shock_matrix_2024-01-01_2026-01-01.csv"
        if not p.exists(): failures.append(f"missing {p}"); continue
        with p.open("r",newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
        ts=[int(r["timestamp_ms"]) for r in rows]
        dup=len(ts)-len(set(ts)); gaps=sum(1 for i in range(1,len(ts)) if ts[i]-ts[i-1]!=STEP_MS); opened=sum(1 for x in ts if x>=1767225600000)
        avail=sum(1 for r in rows if int(r["feature_available_at_ms"])!=int(r["timestamp_ms"])+STEP_MS)
        missing={k:sum(1 for r in rows[12:] if not finite(r.get(k))) for k in SHOCKS}
        label_cov={}
        for tag,bars in HORIZONS.items():
            key=f"future_return_{tag}_atr"; valid=0; cross=0
            for i,r in enumerate(rows):
                if not finite(r.get(key)): continue
                valid+=1
                j=i+bars
                if j>=len(rows) or rows[j].get("timestamp_utc","")[:4]!=r.get("timestamp_utc","")[:4] or int(rows[j]["timestamp_ms"])-int(r["timestamp_ms"])!=bars*STEP_MS: cross+=1
            expected=max(0,len(rows)-2*bars)
            label_cov[tag]={"valid_rows":valid,"missing_rows":len(rows)-valid,"expected_valid_rows":expected,"cross_year_or_noncontiguous_label_violations":cross}
            if valid!=expected or cross: failures.append(f"{sym} future label gate {tag}: valid={valid} expected={expected} cross={cross}")
        if dup or gaps or opened or avail: failures.append(f"{sym} structural integrity dup={dup} gaps={gaps} opened2026={opened} availability={avail}")
        bad_missing={k:v for k,v in missing.items() if v}
        if bad_missing: failures.append(f"{sym} missing shocks after warmup: {bad_missing}")
        report["symbols"][sym]={"rows":len(rows),"first_timestamp_ms":ts[0] if ts else None,"last_timestamp_ms":ts[-1] if ts else None,"duplicate_timestamps":dup,"non_5m_gap_count":gaps,"opened_2026_rows":opened,"feature_availability_violations":avail,"missing_shock_features_after_1h_warmup":missing,"future_label_coverage":label_cov}
    if failures: report["status"]="FAIL"; report["failures"]=failures
    out=root/"event_shock_integrity_v1.json"; out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2,sort_keys=True)); return 0 if not failures else 1
if __name__=="__main__": raise SystemExit(main())
