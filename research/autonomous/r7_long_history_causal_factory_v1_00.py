#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import strategy_factory_causal_next_open_v1_00 as base

PROTECTED = pd.Timestamp("2026-01-01", tz="UTC")
DISCOVERY_START = pd.Timestamp("2017-08-01", tz="UTC")
DISCOVERY_END = pd.Timestamp("2023-01-01", tz="UTC")
CONFIRM_END = pd.Timestamp("2025-01-01", tz="UTC")
PREOOS_END = pd.Timestamp("2026-01-01", tz="UTC")
TAIL_Q = [.05, .10, .20, .30]
ALL_Q = [.05, .10, .20, .30, .70, .80, .90, .95]
HORIZONS = [1, 3, 6, 12, 24, 48]
TIMEFRAMES = ["M15", "H1"]
FULL_DISCOVERY_YEARS = [2018, 2019, 2020, 2021, 2022]


def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    delays = (0.05, 0.10, 0.20, 0.40, 0.80, 1.00)
    for attempt, delay in enumerate(delays):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == len(delays) - 1:
                raise
            time.sleep(delay)


def heartbeat(path: Path | None, completed: int, total: int, stage: str, extra: dict | None = None) -> None:
    if path is None:
        return
    x = {"completed": int(completed), "total": int(total), "stage": stage, "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    if extra:
        x.update(extra)
    atomic_json(path, x)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_exact(path: Path) -> pd.DataFrame:
    if "2026" in path.name.lower():
        raise RuntimeError(f"protected filename forbidden: {path}")
    df = pd.read_csv(path)
    required = {"time", "open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise RuntimeError(f"missing OHLC columns in {path}")
    t = pd.to_datetime(df["time"], utc=True, errors="coerce", format="mixed")
    z = pd.DataFrame({
        "time": t,
        "open": pd.to_numeric(df["open"], errors="coerce"),
        "high": pd.to_numeric(df["high"], errors="coerce"),
        "low": pd.to_numeric(df["low"], errors="coerce"),
        "close": pd.to_numeric(df["close"], errors="coerce"),
    })
    if "volume" in df:
        z["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    z = z.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)
    if (z.time >= PROTECTED).any():
        raise RuntimeError(f"protected 2026 row present: {path}")
    if z.time.min() > pd.Timestamp("2017-08-31 23:59:59", tz="UTC") or z.time.max() < pd.Timestamp("2025-12-31 23:50:00", tz="UTC"):
        raise RuntimeError(f"insufficient long-history coverage: {path}: {z.time.min()} -> {z.time.max()}")
    return z


def resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule = {"M15": "15min", "H1": "1h"}[timeframe]
    expected_rows = {"M15": 3, "H1": 12}[timeframe]
    x = df.set_index("time")
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in x.columns:
        agg["volume"] = "sum"
    grouped = x.resample(rule, label="left", closed="left")
    y = grouped.agg(agg)
    counts = grouped["close"].count()
    # Never synthesize an apparently valid M15/H1 candle from an incomplete 5m bucket.
    y = y.loc[counts.eq(expected_rows)]
    y = y.dropna(subset=["open", "high", "low", "close"]).reset_index()
    return y


def fit_cutpoint(feature: pd.Series, times: pd.Series, quantile: float) -> float:
    mask = (times >= DISCOVERY_START) & (times < DISCOVERY_END) & np.isfinite(feature.to_numpy(dtype=float, copy=True))
    vals = feature.to_numpy(dtype=float, copy=True)[mask.to_numpy()]
    if len(vals) < 1000:
        raise RuntimeError("insufficient discovery values for cutpoint")
    return float(np.quantile(vals, quantile))


def session_mask(df: pd.DataFrame, start: int | None, width: int | None) -> np.ndarray:
    if start is None:
        return np.ones(len(df), dtype=bool)
    hh = df.time.dt.hour.to_numpy()
    return np.asarray([((int(v) - start) % 24) < int(width) for v in hh], dtype=bool)


def apply_rule(df: pd.DataFrame, ft: pd.DataFrame, rule: dict, cut_override: float | None = None) -> np.ndarray:
    x = ft[rule["feature"]].to_numpy(dtype=float, copy=True)
    cut = rule["cutpoint"] if cut_override is None else float(cut_override)
    mask = x > cut if rule["operator"] == "gt" else x < cut
    mask &= session_mask(df, rule["hour_start"], rule["hour_width"])
    return np.asarray(mask, dtype=bool)


def baseline_mask(df: pd.DataFrame, rule: dict) -> np.ndarray:
    return session_mask(df, rule["hour_start"], rule["hour_width"])


def causal_return(df: pd.DataFrame, atr: pd.Series, h: int, direction: int, timeframe: str) -> np.ndarray:
    """Signal is known only after bar i closes; enter open[i+1], exit open[i+h+1].

    Fail closed across missing/resampled gaps and across calendar-year boundaries so
    each temporal gate is measured only on complete within-year holding paths.
    """
    ent = df.open.shift(-1)
    ex = df.open.shift(-(h + 1))
    ret = ((ex - ent) / atr * direction).to_numpy(dtype=float, copy=True)

    years = df.time.dt.year.to_numpy()
    entry_year = df.time.shift(-1).dt.year.to_numpy()
    exit_year = df.time.shift(-(h + 1)).dt.year.to_numpy()
    authorized = np.isin(years, np.arange(2017, 2026))
    same_year = (years == entry_year) & (entry_year == exit_year)

    expected = {"M15": pd.Timedelta(minutes=15), "H1": pd.Timedelta(hours=1)}[timeframe]
    step_ok = df.time.diff().eq(expected).to_numpy()
    bad = (~step_ok).astype(np.int64)
    if len(bad):
        bad[0] = 0
    prefix = np.concatenate(([0], np.cumsum(bad)))
    continuity = np.zeros(len(df), dtype=bool)
    idx = np.arange(len(df))
    valid_idx = idx + h + 1 < len(df)
    iv = idx[valid_idx]
    # Required transitions are bad[i+1] ... bad[i+h+1].
    bad_counts = prefix[iv + h + 2] - prefix[iv + 1]
    continuity[iv] = bad_counts == 0

    valid = np.isfinite(ret) & authorized & same_year & continuity
    ret[~valid] = np.nan
    return ret


def window_mask(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> np.ndarray:
    t = df.time
    return ((t >= start) & (t < end)).to_numpy()


def edge(sel: np.ndarray, base_mask_arr: np.ndarray, ret: np.ndarray, min_n: int) -> dict | None:
    return base.welch_edge(sel, base_mask_arr, ret, min_n)


def hac(sel: np.ndarray, base_mask_arr: np.ndarray, ret: np.ndarray, lag: int, min_n: int) -> dict | None:
    return base.hac_edge(sel, base_mask_arr, ret, max_lag=lag, min_n=min_n)


def bh_qvalues(pvals: list[float]) -> list[float]:
    if not pvals:
        return []
    return base.bh_qvalues(np.asarray(pvals, dtype=float)).tolist()


def stable_rule_id(rule: dict) -> str:
    keys = ["dataset", "timeframe", "feature", "operator", "quantile", "horizon_bars", "direction", "hour_start", "hour_width"]
    payload = {k: rule[k] for k in keys}
    return "R7-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12].upper()


def publish(publisher: str | None, status: str, summary: str, artifacts: list[Path]) -> None:
    if not publisher:
        return
    cmd = ["python", publisher, "--phase", "r7-long-history-causal-factory", "--status", status, "--summary", summary]
    for a in artifacts:
        cmd += ["--artifact", str(a)]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--trials", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=260912)
    ap.add_argument("--publisher")
    args = ap.parse_args()
    if args.trials != 50000 or args.seed != 260912:
        raise ValueError("R7 v1.00 search size and seed are frozen by preregistration")

    data_dir = Path(args.data_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    rng = random.Random(args.seed)

    inputs = [data_dir / "BTCUSDT_spot_5m_2017_2025.csv", data_dir / "ETHUSDT_spot_5m_2017_2025.csv"]
    markets = []
    input_hashes = {}
    heartbeat(progress, 0, args.trials, "load_long_history")
    for path in inputs:
        raw = load_exact(path)
        input_hashes[path.name] = sha256_file(path)
        for tf in TIMEFRAMES:
            df = resample(raw, tf)
            ft, atr = base.features(df)
            markets.append({"dataset": path.name, "timeframe": tf, "df": df, "ft": ft, "atr": atr})
    if len(markets) != 4:
        raise RuntimeError("expected exactly BTC/ETH x M15/H1 markets")

    discovery = []
    seen = set()
    for i in range(args.trials):
        mi = rng.randrange(len(markets))
        m = markets[mi]
        df, ft, atr = m["df"], m["ft"], m["atr"]
        feature = rng.choice(list(ft.columns))
        op = rng.choice(["gt", "lt"])
        tail = rng.choice(TAIL_Q)
        q = 1.0 - tail if op == "gt" else tail
        h = rng.choice(HORIZONS)
        direction = rng.choice([-1, 1])
        hour_start = None
        hour_width = None
        if rng.random() < 0.35:
            hour_start = rng.randrange(24)
            hour_width = rng.choice([2, 4, 6, 8])
        sig = (mi, feature, op, q, h, direction, hour_start, hour_width)
        if sig in seen:
            continue
        seen.add(sig)
        try:
            cut = fit_cutpoint(ft[feature], df.time, q)
        except RuntimeError:
            continue
        rule = {
            "dataset": m["dataset"], "timeframe": m["timeframe"], "market_index": mi,
            "feature": feature, "operator": op, "quantile": q, "cutpoint": cut,
            "horizon_bars": h, "direction": direction,
            "hour_start": hour_start, "hour_width": hour_width,
            "execution": "signal_after_bar_close_entry_next_open_exit_open_after_h_bars",
        }
        rule["candidate_id"] = stable_rule_id(rule)
        sel = apply_rule(df, ft, rule)
        bmask = baseline_mask(df, rule)
        ret = causal_return(df, atr, h, direction, m["timeframe"])
        disc = window_mask(df, DISCOVERY_START, DISCOVERY_END)
        agg = edge(sel & disc, bmask & disc, ret, 300)
        if not agg or agg["edge_atr"] <= 0.018 or agg["p_fast"] >= 0.005:
            continue
        yearly = {}
        positives = 0
        valid = True
        for y in FULL_DISCOVERY_YEARS:
            ym = (df.time.dt.year.to_numpy() == y)
            ys = edge(sel & ym, bmask & ym, ret, 60)
            yearly[str(y)] = ys
            if ys is None:
                valid = False
                break
            if ys["edge_atr"] > 0:
                positives += 1
        if valid and positives >= 4:
            rr = dict(rule)
            rr["discovery_2017_2022"] = agg
            rr["discovery_years_2018_2022"] = yearly
            rr["positive_full_discovery_years"] = positives
            discovery.append(rr)
        if (i + 1) % 500 == 0:
            heartbeat(progress, i + 1, args.trials, "discovery_2017_2022", {"unique_rules": len(seen), "discovery_candidates": len(discovery)})

    # Freeze discovery before independent 2023-2024 confirmation.
    discovery_ids = sorted(r["candidate_id"] for r in discovery)
    discovery_hash = hashlib.sha256("|".join(discovery_ids).encode()).hexdigest()
    heartbeat(progress, len(seen), args.trials, "discovery_frozen_before_2023_2024", {"discovery_candidates": len(discovery), "frozen_ids_sha256": discovery_hash})

    confirms = []
    pvals = []
    for j, r in enumerate(discovery, 1):
        m = markets[r["market_index"]]
        df, ft, atr = m["df"], m["ft"], m["atr"]
        sel = apply_rule(df, ft, r)
        bmask = baseline_mask(df, r)
        ret = causal_return(df, atr, r["horizon_bars"], r["direction"], m["timeframe"])
        y23 = df.time.dt.year.to_numpy() == 2023
        y24 = df.time.dt.year.to_numpy() == 2024
        s23 = edge(sel & y23, bmask & y23, ret, 80)
        s24 = edge(sel & y24, bmask & y24, ret, 80)
        pooled_mask = y23 | y24
        sh = None
        if s23 and s24 and s23["edge_atr"] > 0 and s24["edge_atr"] > 0:
            sh = hac(sel & pooled_mask, bmask & pooled_mask, ret, max(48, 2 * r["horizon_bars"]), 160)
        pvals.append(1.0 if sh is None else sh["p_hac"])
        rr = dict(r)
        rr["confirm_2023"] = s23
        rr["confirm_2024"] = s24
        rr["confirm_2023_2024_hac"] = sh
        confirms.append(rr)
        if j % 200 == 0:
            heartbeat(progress, j, max(1, len(discovery)), "confirmation_2023_2024", {"discovery_candidates": len(discovery)})

    qvals = bh_qvalues(pvals)
    confirmed = []
    for idx, r in enumerate(confirms):
        r["confirmation_bh_q"] = float(qvals[idx]) if qvals else 1.0
        s23, s24, sh = r["confirm_2023"], r["confirm_2024"], r["confirm_2023_2024_hac"]
        if not (s23 and s24 and sh):
            continue
        if not (s23["edge_atr"] > 0 and s24["edge_atr"] > 0 and sh["edge_atr"] > 0.012 and r["confirmation_bh_q"] <= 0.05):
            continue
        # Adjacent discovery-fitted quantile stress on confirmation only.
        qi = ALL_Q.index(r["quantile"])
        neigh = [k for k in (qi - 1, qi + 1) if 0 <= k < len(ALL_Q) and ((r["operator"] == "lt" and ALL_Q[k] <= .30) or (r["operator"] == "gt" and ALL_Q[k] >= .70))]
        m = markets[r["market_index"]]
        df, ft, atr = m["df"], m["ft"], m["atr"]
        xdisc_mask = window_mask(df, DISCOVERY_START, DISCOVERY_END)
        x = ft[r["feature"]].to_numpy(dtype=float, copy=True)
        vals = x[xdisc_mask & np.isfinite(x)]
        ret = causal_return(df, atr, r["horizon_bars"], r["direction"], m["timeframe"])
        bmask = baseline_mask(df, r)
        pooled = (df.time.dt.year.to_numpy() == 2023) | (df.time.dt.year.to_numpy() == 2024)
        stress = []
        robust = False
        for k in neigh:
            nq = ALL_Q[k]
            nc = float(np.quantile(vals, nq))
            nm = apply_rule(df, ft, r, cut_override=nc)
            ns = edge(nm & pooled, bmask & pooled, ret, 120)
            stress.append({"quantile": nq, "cutpoint": nc, "confirm_2023_2024": ns})
            if ns and ns["edge_atr"] > 0.005:
                robust = True
        r["neighbor_stress"] = stress
        if robust:
            confirmed.append(r)

    confirmed_ids = sorted(r["candidate_id"] for r in confirmed)
    confirmed_hash = hashlib.sha256("|".join(confirmed_ids).encode()).hexdigest()
    heartbeat(progress, len(confirmed), max(1, len(confirmed)), "confirmation_frozen_before_2025", {"confirmation_survivors": len(confirmed), "frozen_ids_sha256": confirmed_hash})

    # 2025 is a pre-OOS temporal gate. No rule, threshold or search choice changes here.
    gate_records = []
    gate_pvals = []
    for r in confirmed:
        m = markets[r["market_index"]]
        df, ft, atr = m["df"], m["ft"], m["atr"]
        sel = apply_rule(df, ft, r)
        bmask = baseline_mask(df, r)
        ret = causal_return(df, atr, r["horizon_bars"], r["direction"], m["timeframe"])
        y25 = df.time.dt.year.to_numpy() == 2025
        mo = df.time.dt.month.to_numpy()
        annual = hac(sel & y25, bmask & y25, ret, max(48, 2 * r["horizon_bars"]), 100)
        h1 = edge(sel & y25 & (mo <= 6), bmask & y25 & (mo <= 6), ret, 50)
        h2 = edge(sel & y25 & (mo >= 7), bmask & y25 & (mo >= 7), ret, 50)
        quarters = []
        for a, b in ((1, 3), (4, 6), (7, 9), (10, 12)):
            quarters.append(edge(sel & y25 & (mo >= a) & (mo <= b), bmask & y25 & (mo >= a) & (mo <= b), ret, 25))
        rr = dict(r)
        rr["pre_oos_2025_hac"] = annual
        rr["pre_oos_2025_h1"] = h1
        rr["pre_oos_2025_h2"] = h2
        rr["pre_oos_2025_quarters"] = quarters
        gate_records.append(rr)
        gate_pvals.append(1.0 if annual is None else annual["p_hac"])

    gate_q = bh_qvalues(gate_pvals)
    survivors = []
    for i, r in enumerate(gate_records):
        r["pre_oos_2025_bh_q"] = float(gate_q[i]) if gate_q else 1.0
        annual, h1, h2, quarters = r["pre_oos_2025_hac"], r["pre_oos_2025_h1"], r["pre_oos_2025_h2"], r["pre_oos_2025_quarters"]
        if not (annual and h1 and h2 and all(q is not None for q in quarters)):
            continue
        positive_quarters = sum(q["edge_atr"] > 0 for q in quarters)
        if annual["edge_atr"] > 0.008 and r["pre_oos_2025_bh_q"] <= 0.05 and h1["edge_atr"] > 0 and h2["edge_atr"] > 0 and positive_quarters >= 3:
            r["positive_2025_quarters"] = positive_quarters
            r.pop("market_index", None)
            survivors.append(r)

    survivors.sort(key=lambda r: (r["pre_oos_2025_bh_q"], -r["pre_oos_2025_hac"]["edge_atr"]))
    survivors = survivors[:200]

    result = {
        "schema": 1,
        "phase": "r7-long-history-causal-factory",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protected_2026_untouched": True,
        "chronology": {
            "discovery": "2017-08-01 through 2022-12-31",
            "confirmation": "2023-01-01 through 2024-12-31",
            "pre_oos_gate": "2025-01-01 through 2025-12-31",
        },
        "search": {"seed": args.seed, "trials": args.trials, "timeframes": TIMEFRAMES, "horizons": HORIZONS, "tail_quantiles": TAIL_Q},
        "input_hashes": input_hashes,
        "unique_rules_tested": len(seen),
        "discovery_candidate_count": len(discovery),
        "discovery_frozen_ids_sha256": discovery_hash,
        "confirmation_survivor_count": len(confirmed),
        "confirmation_frozen_ids_sha256": confirmed_hash,
        "pre_oos_survivor_count": len(survivors),
        "survivors": survivors,
        "interpretation": "Survivors are long-history alpha candidates only. They still require explicit economic/cost robustness, concentration/drawdown diagnostics and later broker/MT5 fidelity before any EA promotion.",
    }
    rp = out / "r7_long_history_causal_factory_result.json"
    cp = out / "r7_long_history_causal_factory_survivors.csv"
    atomic_json(rp, result)
    (pd.json_normalize(survivors) if survivors else pd.DataFrame()).to_csv(cp, index=False)
    heartbeat(progress, args.trials, args.trials, "complete", {"discovery_candidates": len(discovery), "confirmation_survivors": len(confirmed), "pre_oos_survivors": len(survivors)})
    status = "PASS" if survivors else "FAIL"
    summary = f"R7 long-history causal factory {status}: {len(survivors)} survivors after 2017-22 discovery, frozen 2023-24 confirmation and frozen 2025 pre-OOS gate; 2026 untouched."
    publish(args.publisher, status, summary, [rp, cp])
    print(json.dumps({"status": status, "trials": args.trials, "unique_rules": len(seen), "discovery_candidates": len(discovery), "confirmation_survivors": len(confirmed), "pre_oos_survivors": len(survivors), "protected_2026_untouched": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
