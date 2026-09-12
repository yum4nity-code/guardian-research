#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r7_long_history_causal_factory_v1_00 as r7

EXPECTED_FACTORY_SHA256 = "aeafdf64cb1d8e60b42fb6e1e3b872fcfcf40949410c0b456f895c250d949b1c"
EXPECTED_SURVIVORS = 8
EXPECTED_INPUT_HASHES = {
    "BTCUSDT_spot_5m_2017_2025.csv": "75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8",
    "ETHUSDT_spot_5m_2017_2025.csv": "21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13",
}
COSTS = {"E1": 0.0005, "STRESS": 0.0010}
PROTECTED = pd.Timestamp("2026-01-01", tz="UTC")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def heartbeat(path: Path | None, completed: int, total: int, stage: str, extra: dict | None = None) -> None:
    if path is None:
        return
    payload = {
        "completed": int(completed),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    atomic_json(path, payload)


def publish(publisher: str | None, status: str, summary: str, artifacts: list[Path]) -> None:
    if not publisher:
        return
    cmd = ["python", publisher, "--phase", "r7-pre-oos-economic-robustness", "--status", status, "--summary", summary]
    for artifact in artifacts:
        cmd += ["--artifact", str(artifact)]
    subprocess.run(cmd, check=True)


def build_market(data_path: Path, timeframe: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    raw = r7.load_exact(data_path)
    if (raw.time >= PROTECTED).any():
        raise RuntimeError(f"protected row present in {data_path}")
    df = r7.resample(raw, timeframe)
    ft, atr = r7.features_contiguous(df, timeframe)
    return df, ft, atr


def extract_nonoverlap_trades(df: pd.DataFrame, ft: pd.DataFrame, atr: pd.Series, rule: dict) -> tuple[pd.DataFrame, dict]:
    mask = r7.apply_rule(df, ft, rule)
    h = int(rule["horizon_bars"])
    direction = int(rule["direction"])
    valid_ret = r7.causal_return(df, atr, h, direction, rule["timeframe"])
    signal_idx = np.flatnonzero(mask & np.isfinite(valid_ret))
    rows = []
    ignored_overlap = 0
    last_exit = None
    for i in signal_idx:
        entry_i = int(i + 1)
        exit_i = int(i + h + 1)
        if exit_i >= len(df):
            continue
        signal_time = df.time.iloc[i]
        entry_time = df.time.iloc[entry_i]
        exit_time = df.time.iloc[exit_i]
        if not (signal_time.year == entry_time.year == exit_time.year):
            continue
        if exit_time >= PROTECTED:
            raise RuntimeError("attempted protected 2026 execution")
        if last_exit is not None and entry_time < last_exit:
            ignored_overlap += 1
            continue
        entry = float(df.open.iloc[entry_i])
        exit_ = float(df.open.iloc[exit_i])
        if not (math.isfinite(entry) and math.isfinite(exit_) and entry > 0 and exit_ > 0):
            continue
        gross = direction * (exit_ / entry - 1.0)
        row = {
            "signal_time": signal_time,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry": entry,
            "exit": exit_,
            "gross_return": gross,
        }
        for name, one_way in COSTS.items():
            row[f"net_{name}"] = gross - 2.0 * one_way
        rows.append(row)
        last_exit = exit_time
    trades = pd.DataFrame(rows)
    if not trades.empty:
        for c in ["signal_time", "entry_time", "exit_time"]:
            trades[c] = pd.to_datetime(trades[c], utc=True)
    return trades, {"raw_valid_signals": int(len(signal_idx)), "ignored_overlap": int(ignored_overlap)}


def max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    equity = series.cumsum()
    peak = equity.cummax()
    return float((equity - peak).min())


def metric_block(trades: pd.DataFrame, col: str) -> dict:
    if trades.empty:
        return {"n": 0, "net_sum": 0.0, "mean": 0.0, "median": 0.0, "win_rate": 0.0, "best": 0.0, "worst": 0.0, "max_drawdown": 0.0}
    x = trades[col].astype(float)
    return {
        "n": int(len(x)),
        "net_sum": float(x.sum()),
        "mean": float(x.mean()),
        "median": float(x.median()),
        "win_rate": float((x > 0).mean()),
        "best": float(x.max()),
        "worst": float(x.min()),
        "max_drawdown": max_drawdown(x),
    }


def subset_metrics(trades: pd.DataFrame) -> dict:
    return {name: metric_block(trades, f"net_{name}") for name in COSTS}


def monthly_diagnostics(trades: pd.DataFrame, col: str) -> dict:
    months = pd.period_range("2018-01", "2025-12", freq="M")
    if trades.empty:
        vals = pd.Series(0.0, index=months)
    else:
        temp = trades.copy()
        temp["month"] = temp.entry_time.dt.tz_convert(None).dt.to_period("M")
        vals = temp.groupby("month")[col].sum().reindex(months, fill_value=0.0)
    roll6 = vals.rolling(6, min_periods=6).sum()
    roll12 = vals.rolling(12, min_periods=12).sum()
    return {
        "monthly": {str(k): float(v) for k, v in vals.items()},
        "rolling_6m_min": None if roll6.dropna().empty else float(roll6.min()),
        "rolling_12m_min": None if roll12.dropna().empty else float(roll12.min()),
        "positive_months": int((vals > 0).sum()),
    }


def evaluate_candidate(trades: pd.DataFrame, rule: dict, accounting: dict) -> dict:
    if trades.empty:
        years = {}
    else:
        years = {str(y): subset_metrics(trades[trades.entry_time.dt.year == y]) for y in range(2018, 2026)}
    discovery = subset_metrics(trades[(trades.entry_time >= pd.Timestamp("2018-01-01", tz="UTC")) & (trades.entry_time < pd.Timestamp("2023-01-01", tz="UTC"))])
    confirmation = subset_metrics(trades[(trades.entry_time >= pd.Timestamp("2023-01-01", tz="UTC")) & (trades.entry_time < pd.Timestamp("2025-01-01", tz="UTC"))])
    pre_oos = subset_metrics(trades[(trades.entry_time >= pd.Timestamp("2025-01-01", tz="UTC")) & (trades.entry_time < PROTECTED)])
    h1 = subset_metrics(trades[(trades.entry_time >= pd.Timestamp("2025-01-01", tz="UTC")) & (trades.entry_time < pd.Timestamp("2025-07-01", tz="UTC"))])
    h2 = subset_metrics(trades[(trades.entry_time >= pd.Timestamp("2025-07-01", tz="UTC")) & (trades.entry_time < PROTECTED)])

    stress_2025 = trades[(trades.entry_time >= pd.Timestamp("2025-01-01", tz="UTC")) & (trades.entry_time < PROTECTED)]["net_STRESS"].astype(float) if not trades.empty else pd.Series(dtype=float)
    top1_removed_2025_stress = 0.0 if stress_2025.empty else float(stress_2025.sum() - stress_2025.max())
    positive_disc_years = sum(1 for y in range(2018, 2023) if years.get(str(y), {}).get("E1", {}).get("net_sum", 0.0) > 0)

    reasons = []
    for y in [2023, 2024, 2025]:
        if years.get(str(y), {}).get("E1", {}).get("n", 0) < 100:
            reasons.append(f"trades_{y}_lt_100")
    if h1["E1"]["n"] < 40:
        reasons.append("trades_2025_h1_lt_40")
    if h2["E1"]["n"] < 40:
        reasons.append("trades_2025_h2_lt_40")
    if positive_disc_years < 4:
        reasons.append("e1_positive_discovery_years_lt_4")
    if discovery["STRESS"]["net_sum"] <= 0:
        reasons.append("stress_discovery_2018_2022_nonpositive")
    for y in [2023, 2024, 2025]:
        if years.get(str(y), {}).get("E1", {}).get("net_sum", 0.0) <= 0:
            reasons.append(f"e1_{y}_nonpositive")
        if years.get(str(y), {}).get("STRESS", {}).get("net_sum", 0.0) <= 0:
            reasons.append(f"stress_{y}_nonpositive")
    if h1["E1"]["net_sum"] <= 0:
        reasons.append("e1_2025_h1_nonpositive")
    if h2["E1"]["net_sum"] <= 0:
        reasons.append("e1_2025_h2_nonpositive")
    if top1_removed_2025_stress <= 0:
        reasons.append("stress_2025_top1_removed_nonpositive")

    monthly = {name: monthly_diagnostics(trades, f"net_{name}") for name in COSTS}
    total_stress = metric_block(trades, "net_STRESS")
    best_trade_share = None
    if total_stress["net_sum"] > 0 and not trades.empty:
        best_trade_share = float(max(0.0, trades["net_STRESS"].max()) / total_stress["net_sum"])

    return {
        "candidate_id": rule["candidate_id"],
        "dataset": rule["dataset"],
        "timeframe": rule["timeframe"],
        "feature": rule["feature"],
        "operator": rule["operator"],
        "quantile": rule["quantile"],
        "cutpoint": rule["cutpoint"],
        "horizon_bars": rule["horizon_bars"],
        "direction": rule["direction"],
        "hour_start": rule["hour_start"],
        "hour_width": rule["hour_width"],
        "execution": rule["execution"],
        "accounting": accounting,
        "years": years,
        "discovery_2018_2022": discovery,
        "confirmation_2023_2024": confirmation,
        "pre_oos_2025": pre_oos,
        "pre_oos_2025_h1": h1,
        "pre_oos_2025_h2": h2,
        "monthly": monthly,
        "best_trade_share_of_total_stress_net": best_trade_share,
        "stress_2025_top1_removed_net_sum": top1_removed_2025_stress,
        "positive_e1_discovery_years_2018_2022": int(positive_disc_years),
        "pass": not reasons,
        "failure_reasons": reasons,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--factory-result", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    factory_path = Path(args.factory_result)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None

    if sha256_file(factory_path) != EXPECTED_FACTORY_SHA256:
        raise RuntimeError("frozen R7 factory result hash mismatch")
    factory = json.loads(factory_path.read_text(encoding="utf-8"))
    survivors = factory.get("survivors", [])
    if len(survivors) != EXPECTED_SURVIVORS:
        raise RuntimeError(f"expected {EXPECTED_SURVIVORS} frozen survivors, found {len(survivors)}")
    if not factory.get("protected_2026_untouched", False):
        raise RuntimeError("upstream protected-data provenance is not clean")

    for name, expected in EXPECTED_INPUT_HASHES.items():
        path = data_dir / name
        if not path.exists():
            raise RuntimeError(f"missing frozen input: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"input hash mismatch for {name}: {actual}")

    heartbeat(progress, 0, len(survivors), "load_and_verify", {"survivors": len(survivors)})
    cache: dict[tuple[str, str], tuple[pd.DataFrame, pd.DataFrame, pd.Series]] = {}
    diagnostics = []
    for idx, rule in enumerate(survivors, 1):
        key = (rule["dataset"], rule["timeframe"])
        if key not in cache:
            cache[key] = build_market(data_dir / rule["dataset"], rule["timeframe"])
        df, ft, atr = cache[key]
        trades, accounting = extract_nonoverlap_trades(df, ft, atr, rule)
        diagnostics.append(evaluate_candidate(trades, rule, accounting))
        heartbeat(progress, idx, len(survivors), "evaluate", {"candidate_id": rule["candidate_id"], "passes_so_far": sum(1 for d in diagnostics if d["pass"])})

    passed = [d for d in diagnostics if d["pass"]]
    result = {
        "schema": 1,
        "phase": "r7-pre-oos-economic-robustness",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "factory_result_sha256": EXPECTED_FACTORY_SHA256,
        "input_hashes": EXPECTED_INPUT_HASHES,
        "candidate_count": len(diagnostics),
        "pass_count": len(passed),
        "passed_candidate_ids": [d["candidate_id"] for d in passed],
        "cost_profiles": {k: {"one_way_fraction": v, "round_trip_bps": float(v * 2 * 10000)} for k, v in COSTS.items()},
        "protected_2026_opened": False,
        "interpretation": "Reject-only economic robustness on frozen R7 survivors using non-overlapping causal trades. PASS is not EA or broker-specific validation.",
        "diagnostics": diagnostics,
    }
    result_path = out / "r7_pre_oos_economic_robustness_result.json"
    atomic_json(result_path, result)

    rows = []
    for d in diagnostics:
        rows.append({
            "candidate_id": d["candidate_id"],
            "dataset": d["dataset"],
            "timeframe": d["timeframe"],
            "feature": d["feature"],
            "horizon_bars": d["horizon_bars"],
            "pass": d["pass"],
            "failure_reasons": ";".join(d["failure_reasons"]),
            "trades_2023": d["years"].get("2023", {}).get("E1", {}).get("n", 0),
            "trades_2024": d["years"].get("2024", {}).get("E1", {}).get("n", 0),
            "trades_2025": d["years"].get("2025", {}).get("E1", {}).get("n", 0),
            "e1_2023": d["years"].get("2023", {}).get("E1", {}).get("net_sum", 0.0),
            "e1_2024": d["years"].get("2024", {}).get("E1", {}).get("net_sum", 0.0),
            "e1_2025": d["years"].get("2025", {}).get("E1", {}).get("net_sum", 0.0),
            "stress_2023": d["years"].get("2023", {}).get("STRESS", {}).get("net_sum", 0.0),
            "stress_2024": d["years"].get("2024", {}).get("STRESS", {}).get("net_sum", 0.0),
            "stress_2025": d["years"].get("2025", {}).get("STRESS", {}).get("net_sum", 0.0),
            "stress_2025_top1_removed": d["stress_2025_top1_removed_net_sum"],
        })
    csv_path = out / "r7_pre_oos_economic_robustness_diagnostics.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    status = "PASS" if passed else "FAIL"
    summary = f"R7 pre-OOS economic robustness {status}: {len(passed)}/{len(diagnostics)} frozen candidates pass non-overlap and 10/20 bps round-trip reject-only cost gates; 2026 untouched."
    heartbeat(progress, len(survivors), len(survivors), "complete", {"passes": len(passed), "status": status})
    publish(args.publisher, status, summary, [result_path, csv_path])
    print(json.dumps({"status": status, "candidate_count": len(diagnostics), "pass_count": len(passed), "protected_2026_opened": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
