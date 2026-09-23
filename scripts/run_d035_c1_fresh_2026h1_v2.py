#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "D035-C1-FRESH-2026H1-V2-1.0"
SAMPLE_START = pd.Timestamp("2026-01-01T00:00:00Z")
SAMPLE_END_EXCLUSIVE = pd.Timestamp("2026-07-01T00:00:00Z")
SAMPLE_END = SAMPLE_END_EXCLUSIVE - pd.Timedelta(seconds=1)
WARMUP_START = pd.Timestamp("2025-11-01T00:00:00Z")
PRIMARY_TARGET = "XLMUSD"
DUAL_WINDOW_MIN = 5
HORIZONS = (15, 30)
MIN_FRESH_EVENTS_FOR_NONSPARSE = 100

def log(msg: str) -> None:
    print(f"[D035-C1] {msg}", flush=True)

def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("d035_base_full", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import base analyzer: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["d035_base_full"] = mod
    spec.loader.exec_module(mod)
    required = [
        "SOURCE_SYMBOLS","CONTROL_LOOKBACK_DAYS","load_metrics","load_klines",
        "exact_5m_source","causal_shocks","merge_source_events","load_cfd_files",
        "canonical_cfd_symbol","calibrate_offsets","apply_offsets",
        "build_event_exclusion_intervals","first_row_at_or_after",
        "exec_short_return","mid_short_return","causal_control_median"
    ]
    missing = [x for x in required if not hasattr(mod, x)]
    if missing:
        raise RuntimeError(f"Base analyzer missing required API: {missing}")
    return mod

def build_causal_dual_events(btc: pd.DataFrame, eth: pd.DataFrame) -> pd.DataFrame:
    raw = pd.concat([btc, eth], ignore_index=True)
    if raw.empty:
        return pd.DataFrame()
    raw = raw.sort_values("event_time_utc").reset_index(drop=True)
    rows = []
    i = 0
    while i < len(raw):
        first = raw.iloc[i].copy()
        group = [first]
        j = i + 1
        while (
            j < len(raw)
            and raw.loc[j, "event_time_utc"] - first["event_time_utc"]
            <= pd.Timedelta(minutes=DUAL_WINDOW_MIN)
        ):
            group.append(raw.iloc[j].copy())
            j += 1
        sources = sorted(set(str(g["source"]) for g in group))
        if sources == ["BTCUSD", "ETHUSD"]:
            later = max(g["event_time_utc"] for g in group)
            earlier = min(g["event_time_utc"] for g in group)
            row = first.copy()
            row["event_time_utc"] = later
            row["first_source_time_utc"] = earlier
            row["confirmation_delay_min"] = (later - earlier).total_seconds() / 60.0
            row["sources"] = "BTCUSD+ETHUSD"
            row["source_count"] = 2
            row["ret5_pct"] = min(float(g["ret5_pct"]) for g in group)
            row["oi_chg5_pct"] = min(float(g["oi_chg5_pct"]) for g in group)
            row["ret_q10"] = min(float(g["ret_q10"]) for g in group)
            row["oi_q10"] = min(float(g["oi_q10"]) for g in group)
            rows.append(row)
        i = j
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("event_time_utc").reset_index(drop=True)

def bootstrap_day_mean(df: pd.DataFrame, col: str, reps: int = 20000, seed: int = 35001):
    z = df.dropna(subset=[col]).copy()
    if z.empty:
        return {"days":0,"reps":reps,"mean":None,"q10":None,"q05":None,"q025":None,"p_mean_le_0":None}
    z["day"] = z["event_time_utc"].dt.floor("D")
    groups = [g[col].to_numpy(float) for _, g in z.groupby("day", sort=True)]
    if len(groups) < 10:
        return {"days":len(groups),"reps":reps,"mean":float(z[col].mean()),"q10":None,"q05":None,"q025":None,"p_mean_le_0":None}
    rng = np.random.default_rng(seed)
    vals = np.empty(reps, dtype=float)
    n = len(groups)
    for i in range(reps):
        picks = rng.integers(0, n, size=n)
        total = 0.0
        count = 0
        for j in picks:
            arr = groups[j]
            total += float(arr.sum())
            count += len(arr)
        vals[i] = total / count
    return {
        "days": len(groups),
        "reps": reps,
        "mean": float(z[col].mean()),
        "q10_one_sided90_lower": float(np.quantile(vals, 0.10)),
        "q05_two_sided90_lower": float(np.quantile(vals, 0.05)),
        "q025_two_sided95_lower": float(np.quantile(vals, 0.025)),
        "median_bootstrap_mean": float(np.median(vals)),
        "p_boot_mean_le_0": float(np.mean(vals <= 0)),
    }

def summarize(g: pd.DataFrame) -> dict:
    out = {
        "n": int(g["exec_short_15m_bps"].notna().sum()),
        "mean_entry_spread_bps": float(g["entry_spread_bps"].mean()),
        "mean_exec_15m_bps": float(g["exec_short_15m_bps"].mean()),
        "median_exec_15m_bps": float(g["exec_short_15m_bps"].median()),
        "mean_exec_30m_bps": float(g["exec_short_30m_bps"].mean()),
        "mean_control_15m_bps": float(g["control_15m_bps"].mean()),
        "mean_diff_15m_bps": float(g["diff_15m_bps"].mean()),
    }
    out["bootstrap_raw15"] = bootstrap_day_mean(g, "exec_short_15m_bps", seed=35001)
    out["bootstrap_diff15"] = bootstrap_day_mean(g, "diff_15m_bps", seed=35002)
    return out

def trim_best(g: pd.DataFrame, col: str, pct: float) -> dict:
    a = g[col].dropna().to_numpy(float)
    if not len(a):
        return {"n":0,"mean":None}
    k = max(1, int(math.ceil(len(a) * pct)))
    s = np.sort(a)
    kept = s[:-k] if k < len(s) else np.array([], dtype=float)
    return {"removed":k,"n":int(len(kept)),"mean":float(kept.mean()) if len(kept) else None}

def month_table(g: pd.DataFrame) -> pd.DataFrame:
    z = g.copy()
    z["month"] = z["event_time_utc"].dt.tz_convert("UTC").dt.strftime("%Y-%m")
    return z.groupby("month", sort=True).agg(
        n=("exec_short_15m_bps","count"),
        mean_exec_15m_bps=("exec_short_15m_bps","mean"),
        median_exec_15m_bps=("exec_short_15m_bps","median"),
        mean_diff_15m_bps=("diff_15m_bps","mean"),
        mean_exec_30m_bps=("exec_short_30m_bps","mean"),
    ).reset_index()

def build_returns(events, target_df, control_events, base):
    event_ns = base.build_event_exclusion_intervals(control_events)
    x = target_df.reset_index(drop=True)
    rows = []
    total = len(events)
    started = time.monotonic()
    for idx, (_, e) in enumerate(events.iterrows(), start=1):
        ts = e["event_time_utc"]
        ent = base.first_row_at_or_after(x, ts, tolerance_min=2)
        if ent is None:
            continue
        entry_mid = float(ent["mid_first"])
        if entry_mid <= 0:
            continue
        row = {
            "event_time_utc": ts,
            "first_source_time_utc": e["first_source_time_utc"],
            "confirmation_delay_min": float(e["confirmation_delay_min"]),
            "entry_time_utc": ent["utc_ts"],
            "entry_bid": float(ent["bid_first"]),
            "entry_ask": float(ent["ask_first"]),
            "entry_mid": entry_mid,
            "entry_spread_bps": ((float(ent["ask_first"]) - float(ent["bid_first"])) / entry_mid * 10000.0),
        }
        for h in HORIZONS:
            ex = base.first_row_at_or_after(x, ts + pd.Timedelta(minutes=h), tolerance_min=2)
            if ex is None:
                row[f"exec_short_{h}m_bps"] = np.nan
                row[f"mid_short_{h}m_bps"] = np.nan
            else:
                row[f"exec_short_{h}m_bps"] = base.exec_short_return(float(ent["bid_first"]), float(ex["ask_first"]))
                row[f"mid_short_{h}m_bps"] = base.mid_short_return(entry_mid, float(ex["mid_first"]))
        row["control_15m_bps"] = base.causal_control_median(x, ts, 15, event_ns)
        if np.isfinite(row["exec_short_15m_bps"]) and np.isfinite(row["control_15m_bps"]):
            row["diff_15m_bps"] = row["exec_short_15m_bps"] - row["control_15m_bps"]
        else:
            row["diff_15m_bps"] = np.nan
        rows.append(row)
        if idx % 100 == 0 or idx == total:
            elapsed = time.monotonic() - started
            log(f"events {idx}/{total} elapsed={elapsed:.1f}s")
    return pd.DataFrame(rows)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-analyzer", required=True, type=Path)
    ap.add_argument("--cfd-dir", required=True, type=Path)
    ap.add_argument("--cache-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    base = load_base(args.base_analyzer)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    log("FRESH 2026-H1 ONLY. PRIMARY TARGET XLMUSD ONLY. NO RETUNING.")

    source5 = {}
    klines_1m = {}
    for sym in ["BTCUSDT","ETHUSDT"]:
        m, _ = base.load_metrics(args.cache_dir, sym, WARMUP_START, SAMPLE_END_EXCLUSIVE)
        k, _ = base.load_klines(args.cache_dir, sym, WARMUP_START, SAMPLE_END_EXCLUSIVE)
        klines_1m[sym] = k
        source5[sym] = base.exact_5m_source(k, m)

    btc_ev = base.causal_shocks(source5["BTCUSDT"], "BTCUSDT")
    eth_ev = base.causal_shocks(source5["ETHUSDT"], "ETHUSDT")
    all_events = base.merge_source_events(btc_ev, eth_ev)
    dual = build_causal_dual_events(btc_ev, eth_ev)
    dual = dual[(dual["event_time_utc"] >= SAMPLE_START) & (dual["event_time_utc"] < SAMPLE_END_EXCLUSIVE)].copy()
    log(f"causal dual-source events in 2026-H1: {len(dual)}")

    cfd = base.load_cfd_files(args.cfd_dir)
    canon = {k: base.canonical_cfd_symbol(k) for k in cfd}
    allowed = {"BTCUSD","XLMUSD"}
    seen = set(canon.values())
    if not {"BTCUSD","XLMUSD"}.issubset(seen):
        raise RuntimeError(f"Need BTCUSD and XLMUSD only; found canonical symbols={sorted(seen)}")
    extras = sorted(seen - allowed)
    if extras:
        raise RuntimeError(f"Protected target scope violation: extra CFD exports present: {extras}")

    btc_key = next(k for k,v in canon.items() if v == "BTCUSD")
    xlm_key = next(k for k,v in canon.items() if v == "XLMUSD")

    offset_qa = base.calibrate_offsets(cfd[btc_key], klines_1m["BTCUSDT"], fixed_offset=None)
    offset_qa.to_csv(args.out_dir / "D035_C1_OFFSET_QA.csv", index=False)
    usable = int(offset_qa["usable"].sum())
    if usable < max(4, int(0.70 * len(offset_qa))):
        raise RuntimeError(f"UTC alignment QA failed: {usable}/{len(offset_qa)} usable weeks")

    xlm = base.apply_offsets(cfd[xlm_key], offset_qa)
    xlm = xlm[(xlm["utc_ts"] >= SAMPLE_START) & (xlm["utc_ts"] < SAMPLE_END_EXCLUSIVE + pd.Timedelta(minutes=31))].copy()
    if xlm.empty:
        raise RuntimeError("No aligned XLMUSD rows in 2026-H1.")
    min_ts = xlm["utc_ts"].min()
    max_ts = xlm["utc_ts"].max()
    if min_ts > pd.Timestamp("2026-01-07T00:00:00Z"):
        raise RuntimeError(f"XLMUSD coverage starts too late: {min_ts}")
    if max_ts < pd.Timestamp("2026-06-25T00:00:00Z"):
        raise RuntimeError(f"XLMUSD coverage ends too early: {max_ts}")
    if (xlm["utc_ts"] >= SAMPLE_END_EXCLUSIVE + pd.Timedelta(days=1)).any():
        raise RuntimeError("Post-H1 target row detected after alignment.")

    er = build_returns(dual, xlm, all_events, base)
    if not er.empty:
        er = er[(er["event_time_utc"] >= SAMPLE_START) & (er["event_time_utc"] < SAMPLE_END_EXCLUSIVE)].copy()
    er.to_csv(args.out_dir / "D035_C1_XLM_EVENT_RETURNS.csv", index=False)
    dual.to_csv(args.out_dir / "D035_C1_CAUSAL_DUAL_EVENTS.csv", index=False)

    primary = summarize(er) if not er.empty else {
        "n":0,"mean_exec_15m_bps":None,"median_exec_15m_bps":None,
        "mean_exec_30m_bps":None,"mean_control_15m_bps":None,"mean_diff_15m_bps":None,
        "bootstrap_raw15":{"q10_one_sided90_lower":None},
        "bootstrap_diff15":{"q10_one_sided90_lower":None}
    }

    months = month_table(er) if not er.empty else pd.DataFrame()
    months.to_csv(args.out_dir / "D035_C1_MONTHLY.csv", index=False)

    n = int(primary["n"])
    mean15 = primary["mean_exec_15m_bps"]
    q10 = primary["bootstrap_raw15"].get("q10_one_sided90_lower")
    if n < MIN_FRESH_EVENTS_FOR_NONSPARSE:
        existence = "SPARSE_POSITIVE" if (mean15 is not None and mean15 > 0) else "NEGATIVE"
        support = "SPARSE"
    elif mean15 is None or mean15 <= 0:
        existence = "NEGATIVE"
        support = "ADEQUATE"
    elif q10 is not None and q10 > 0:
        existence = "POSITIVE_CONFIRMED"
        support = "ADEQUATE"
    else:
        existence = "POSITIVE_UNCERTAIN"
        support = "ADEQUATE"

    economic = "MINI_EDGE" if (mean15 is not None and mean15 > 0) else "NO_POSITIVE_EXECUTABLE_EDGE"

    result = {
        "schema":1,
        "version":VERSION,
        "status":"COMPLETE_FRESH_2026H1_CONFIRMATION",
        "candidate_id":"D035-C1-XLMUSD-DUAL-SOURCE",
        "window":{"start":str(SAMPLE_START),"end_exclusive":str(SAMPLE_END_EXCLUSIVE)},
        "frozen_rule":{
            "sources":["BTCUSDT","ETHUSDT"],"dual_window_min":5,
            "signal_time":"later/second shock","target":"XLMUSD",
            "direction":"SHORT","primary_horizon_min":15,"diagnostic_horizon_min":[30]
        },
        "source_events":int(len(dual)),
        "primary":primary,
        "trim_best_1pct":trim_best(er,"exec_short_15m_bps",0.01) if not er.empty else None,
        "monthly":months.to_dict(orient="records"),
        "classification":{
            "existence":existence,
            "support":support,
            "economic_size":economic,
            "ensemble_status":"NOT_TESTED",
            "production_status":"NOT_PRODUCTION_READY"
        },
        "protected_scope":{
            "2026_h1_opened":True,
            "jul_dec_2026_opened":False,
            "other_target_cfds_opened":False
        },
        "retuning_performed":False,
        "live_deployment_authorized":False
    }
    (args.out_dir / "D035_C1_RESULT.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("=== D035-C1 FRESH 2026-H1 RECEIPT ===")
    print(json.dumps({
        "version":VERSION,
        "candidate":"D035-C1-XLMUSD-DUAL-SOURCE",
        "source_events":len(dual),
        "primary":primary,
        "trim_best_1pct":result["trim_best_1pct"],
        "classification":result["classification"],
        "jul_dec_2026_opened":False,
        "other_target_cfds_opened":False,
        "retuning_performed":False,
        "output":str(args.out_dir)
    }, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
