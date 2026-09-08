#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json, math, statistics
from pathlib import Path

STEP_MS = 300000
HORIZONS = {"15m":3,"30m":6,"1h":12,"2h":24,"4h":48}
BASE_FEATURES = [
    "oi_change_15m_pct","oi_change_1h_pct","oi_accel_15m_pctpt","atr_slope_3bar_pct","range_atr",
    "mark_index_bps_change_15m","mark_index_bps_change_1h","premium_index_change_15m","premium_index_change_1h",
    "taker_imbalance_diff_change_15m","taker_imbalance_diff_change_1h",
    "spot_taker_imbalance_change_15m","perp_taker_imbalance_change_15m",
    "perp_spot_basis_bps_change_15m","perp_spot_basis_bps_change_1h",
]


def fnum(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError):
        return None


def load_csv(path: Path):
    out={}
    with path.open("r",newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ts=int(r["timestamp_ms"])
            if ts >= 1767225600000:  # 2026-01-01 UTC
                break
            out[ts]=r
    return out


def add_trailing_shocks(rows):
    specs=[("spot_quote_volume","spot_volume_shock_1h",1e-12),("perp_quote_volume","perp_volume_shock_1h",1e-12),("spot_trade_count","spot_trade_shock_1h",1.0),("perp_trade_count","perp_trade_shock_1h",1.0)]
    for i,row in enumerate(rows):
        for src,dst,eps in specs:
            if i<12:
                row[dst]=""; continue
            prev=[fnum(rows[j].get(src)) for j in range(i-12,i)]
            cur=fnum(row.get(src))
            if cur is None or any(v is None for v in prev): row[dst]=""; continue
            med=statistics.median(prev)
            row[dst]=math.log((cur+eps)/(med+eps))


def add_future_labels(rows):
    for i,row in enumerate(rows):
        close=fnum(row.get("close")); atr=fnum(row.get("atr14")); ts=int(row["timestamp_ms"])
        for tag,bars in HORIZONS.items():
            keys=[f"future_return_{tag}_atr",f"future_mfe_{tag}_atr",f"future_mae_{tag}_atr",f"future_excursion_bias_{tag}_atr",f"future_first_touch_1atr_{tag}"]
            for k in keys: row[k]=""
            j=i+bars
            if close is None or atr is None or atr<=0 or j>=len(rows): continue
            if int(rows[j]["timestamp_ms"])-ts != bars*STEP_MS: continue
            path=rows[i+1:j+1]
            vals=[]; valid=True
            for x in path:
                hi=fnum(x.get("high")); lo=fnum(x.get("low"))
                if hi is None or lo is None: valid=False; break
                vals.append((hi,lo))
            final=fnum(rows[j].get("close"))
            if not valid or final is None: continue
            mfe=max((hi-close)/atr for hi,_ in vals)
            mae=max((close-lo)/atr for _,lo in vals)
            row[f"future_return_{tag}_atr"]=(final-close)/atr
            row[f"future_mfe_{tag}_atr"]=mfe
            row[f"future_mae_{tag}_atr"]=mae
            row[f"future_excursion_bias_{tag}_atr"]=mfe-mae
            touch="NONE"
            up=close+atr; dn=close-atr
            for hi,lo in vals:
                u=hi>=up; d=lo<=dn
                if u and d: touch="AMBIGUOUS_SAME_BAR"; break
                if u: touch="UP"; break
                if d: touch="DOWN"; break
            row[f"future_first_touch_1atr_{tag}"]=touch


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--features-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    ap.add_argument("--derivative-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1")
    ap.add_argument("--flow-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1")
    ap.add_argument("--output-dir",default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\event_shock_v1")
    a=ap.parse_args(); out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    manifest={"schema":1,"phase":"H-A","protected_2026_untouched":True,"news_mask_applied":False,"propfirm_tradability_authorized":False,"news_policy":"Historical news mask is required before any event candidate can be promoted as prop-firm tradable.","horizons":HORIZONS,"symbols":{}}
    for sym in ("BTCUSDT","ETHUSDT"):
        fp=sorted(Path(a.features_dir).glob(f"{sym}_bybit_5m_oi_price_*_features_v1.csv"));
        if len(fp)!=1: raise RuntimeError(f"expected one feature file for {sym}, got {len(fp)}")
        dp=Path(a.derivative_dir)/f"{sym}_derivative_context_features_v1.csv"
        op=Path(a.flow_dir)/f"{sym}_binance_spot_um_5m_orderflow_2024-01-01_2026-01-01.csv"
        if not dp.exists() or not op.exists(): raise RuntimeError(f"missing H-A input for {sym}")
        base=load_csv(fp[0]); der=load_csv(dp); flow=load_csv(op)
        common=sorted(set(base)&set(der)&set(flow))
        rows=[]
        for ts in common:
            b=base[ts]; d=der[ts]; o=flow[ts]
            row=dict(b)
            for k in BASE_FEATURES:
                if k in d: row[k]=d[k]
                if k in o: row[k]=o[k]
            for k in ("spot_quote_volume","perp_quote_volume","spot_trade_count","perp_trade_count"):
                row[k]=o.get(k,"")
            row["feature_available_at_ms"]=ts+STEP_MS
            rows.append(row)
        add_trailing_shocks(rows); add_future_labels(rows)
        path=out/f"{sym}_event_shock_matrix_2024-01-01_2026-01-01.csv"
        with path.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        manifest["symbols"][sym]={"rows":len(rows),"first_timestamp_ms":int(rows[0]["timestamp_ms"]),"last_timestamp_ms":int(rows[-1]["timestamp_ms"]),"output_file":str(path)}
        print(f"{sym}: rows={len(rows)} output={path}")
    mp=out/"event_shock_manifest_v1.json"; mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(f"Manifest: {mp}")
    return 0

if __name__=="__main__": raise SystemExit(main())
