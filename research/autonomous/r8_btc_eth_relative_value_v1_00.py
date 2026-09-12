#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROTECTED = pd.Timestamp("2026-01-01", tz="UTC")
DISC_START = pd.Timestamp("2018-01-01", tz="UTC")
DISC_END = pd.Timestamp("2023-01-01", tz="UTC")
CONF_END = pd.Timestamp("2025-01-01", tz="UTC")
PREOOS_END = pd.Timestamp("2026-01-01", tz="UTC")
LOOKBACKS = [72, 168, 336]
ENTRY_ZS = [1.5, 2.0, 2.5]
EXIT_ZS = [0.0, 0.5]
MAX_HOLDS = [24, 48, 96]
COSTS = {"E1": 0.001, "STRESS": 0.002}


def atomic_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def heartbeat(path: Path | None, done: int, total: int, stage: str, extra: dict | None = None) -> None:
    if path is None:
        return
    x = {"completed": int(done), "total": int(total), "stage": stage, "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    if extra:
        x.update(extra)
    atomic_json(path, x)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_market(path: Path) -> pd.DataFrame:
    if "2026" in path.name.lower():
        raise RuntimeError(f"protected filename forbidden: {path}")
    df = pd.read_csv(path)
    req = {"time", "open", "high", "low", "close"}
    if not req.issubset(df.columns):
        raise RuntimeError(f"missing OHLC columns: {path}")
    z = pd.DataFrame({
        "time": pd.to_datetime(df["time"], utc=True, errors="coerce", format="mixed"),
        "open": pd.to_numeric(df["open"], errors="coerce"),
        "high": pd.to_numeric(df["high"], errors="coerce"),
        "low": pd.to_numeric(df["low"], errors="coerce"),
        "close": pd.to_numeric(df["close"], errors="coerce"),
    }).dropna().sort_values("time").reset_index(drop=True)
    if z.time.duplicated().any():
        raise RuntimeError(f"duplicate timestamps: {path}")
    if (z.time >= PROTECTED).any():
        raise RuntimeError(f"protected 2026 row present: {path}")
    return z


def resample_h1(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index("time")
    g = x.resample("1h", label="left", closed="left")
    y = g.agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    count = g["close"].count()
    y = y.loc[count.eq(12)].dropna().reset_index()
    return y


def align_pair(btc: pd.DataFrame, eth: pd.DataFrame) -> pd.DataFrame:
    b = btc.rename(columns={c: f"btc_{c}" for c in ["open", "high", "low", "close"]})
    e = eth.rename(columns={c: f"eth_{c}" for c in ["open", "high", "low", "close"]})
    z = b.merge(e, on="time", how="inner").sort_values("time").reset_index(drop=True)
    if (z.time >= PROTECTED).any():
        raise RuntimeError("protected rows after alignment")
    return z


def add_zscore(df: pd.DataFrame, lookback: int) -> np.ndarray:
    spread = np.log(df.btc_close) - np.log(df.eth_close)
    breaks = df.time.diff().ne(pd.Timedelta(hours=1))
    if len(breaks):
        breaks.iloc[0] = True
    seg = breaks.cumsum()
    out = pd.Series(np.nan, index=df.index, dtype=float)
    for _, idx in df.groupby(seg, sort=False).groups.items():
        s = spread.loc[idx]
        mu = s.rolling(lookback, min_periods=lookback).mean().shift(1)
        sd = s.rolling(lookback, min_periods=lookback).std(ddof=1).shift(1).replace(0, np.nan)
        out.loc[idx] = (s - mu) / sd
    return out.to_numpy(dtype=float, copy=True)


def exit_condition(z: float, side: int, exit_z: float) -> bool:
    if not np.isfinite(z):
        return False
    if exit_z == 0.0:
        return z <= 0.0 if side == -1 else z >= 0.0
    return abs(z) <= exit_z


def simulate(df: pd.DataFrame, z: np.ndarray, entry_z: float, exit_z: float, max_hold: int) -> list[dict]:
    trades: list[dict] = []
    n = len(df)
    i = 0
    while i < n - 2:
        zi = z[i]
        if not np.isfinite(zi) or abs(zi) < entry_z:
            i += 1
            continue
        side = -1 if zi > 0 else 1  # +1 long BTC/short ETH, -1 short BTC/long ETH
        entry_idx = i + 1
        if entry_idx >= n:
            break
        if df.time.iloc[entry_idx] - df.time.iloc[i] != pd.Timedelta(hours=1):
            i += 1
            continue
        planned_exit = min(entry_idx + max_hold, n - 1)
        exit_idx = planned_exit
        reason = "max_hold"
        valid_path = True
        last_decision = min(entry_idx + max_hold - 1, n - 2)
        for k in range(entry_idx, last_decision + 1):
            if df.time.iloc[k] - df.time.iloc[k - 1] != pd.Timedelta(hours=1):
                valid_path = False
                break
            if exit_condition(z[k], side, exit_z):
                if df.time.iloc[k + 1] - df.time.iloc[k] != pd.Timedelta(hours=1):
                    valid_path = False
                    break
                exit_idx = k + 1
                reason = "reversion"
                break
        if not valid_path or exit_idx <= entry_idx:
            i += 1
            continue
        section = df.time.iloc[entry_idx:exit_idx + 1]
        if len(section) != (exit_idx - entry_idx + 1) or section.diff().dropna().ne(pd.Timedelta(hours=1)).any():
            i += 1
            continue
        entry_year = int(df.time.iloc[entry_idx].year)
        exit_year = int(df.time.iloc[exit_idx].year)
        if entry_year != exit_year:
            i = exit_idx
            continue
        br = float(df.btc_open.iloc[exit_idx] / df.btc_open.iloc[entry_idx] - 1.0)
        er = float(df.eth_open.iloc[exit_idx] / df.eth_open.iloc[entry_idx] - 1.0)
        gross = 0.5 * side * br + 0.5 * (-side) * er
        trades.append({
            "signal_time": df.time.iloc[i], "entry_time": df.time.iloc[entry_idx], "exit_time": df.time.iloc[exit_idx],
            "side": side, "entry_z": float(zi), "hold_hours": int(exit_idx - entry_idx), "exit_reason": reason,
            "gross": gross, "E1": gross - COSTS["E1"], "STRESS": gross - COSTS["STRESS"],
        })
        i = exit_idx
    return trades


def p_two_sided(values: np.ndarray) -> float:
    if len(values) < 2:
        return 1.0
    mu = float(np.mean(values)); sd = float(np.std(values, ddof=1))
    if sd <= 0:
        return 0.0 if mu != 0 else 1.0
    z = mu / (sd / math.sqrt(len(values)))
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


def bh_qvalues(pvals: list[float]) -> list[float]:
    n = len(pvals)
    if n == 0:
        return []
    order = np.argsort(np.asarray(pvals))
    q = np.ones(n)
    prev = 1.0
    for j in range(n - 1, -1, -1):
        idx = int(order[j]); rank = j + 1
        val = min(prev, float(pvals[idx]) * n / rank)
        q[idx] = val; prev = val
    return q.tolist()


def subset(trades: list[dict], start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
    return [t for t in trades if start <= t["entry_time"] < end]


def metrics(trades: list[dict]) -> dict:
    out = {"n": len(trades)}
    for key in ["gross", "E1", "STRESS"]:
        a = np.asarray([t[key] for t in trades], dtype=float)
        out[key] = {
            "mean": float(np.mean(a)) if len(a) else None,
            "net_sum": float(np.sum(a)) if len(a) else None,
            "median": float(np.median(a)) if len(a) else None,
            "p": p_two_sided(a) if len(a) else 1.0,
        }
    return out


def candidate_id(rule: dict) -> str:
    payload = json.dumps(rule, sort_keys=True, separators=(",", ":"))
    return "R8-" + hashlib.sha256(payload.encode()).hexdigest()[:12].upper()


def publish(publisher: str | None, status: str, summary: str, artifacts: list[Path]) -> None:
    if not publisher:
        return
    cmd = ["python", publisher, "--phase", "r8-btc-eth-relative-value", "--status", status, "--summary", summary]
    for a in artifacts:
        cmd += ["--artifact", str(a)]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()
    data_dir = Path(args.data_dir); out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    btc_path = data_dir / "BTCUSDT_spot_5m_2017_2025.csv"
    eth_path = data_dir / "ETHUSDT_spot_5m_2017_2025.csv"
    heartbeat(progress, 0, 54, "load")
    btc = resample_h1(load_market(btc_path)); eth = resample_h1(load_market(eth_path)); df = align_pair(btc, eth)
    if df.time.min() > pd.Timestamp("2017-09-01", tz="UTC") or df.time.max() < pd.Timestamp("2025-12-31 22:00", tz="UTC"):
        raise RuntimeError(f"insufficient pair history: {df.time.min()} -> {df.time.max()}")
    zscores = {lb: add_zscore(df, lb) for lb in LOOKBACKS}
    input_hashes = {btc_path.name: sha256_file(btc_path), eth_path.name: sha256_file(eth_path)}

    discovery = []
    done = 0
    for lb in LOOKBACKS:
        for ez in ENTRY_ZS:
            for xz in EXIT_ZS:
                for mh in MAX_HOLDS:
                    rule = {"lookback_hours": lb, "entry_abs_z": ez, "exit_abs_z": xz, "max_hold_hours": mh}
                    cid = candidate_id(rule)
                    trades = simulate(df, zscores[lb], ez, xz, mh)
                    d = subset(trades, DISC_START, DISC_END); m = metrics(d)
                    yearly = {}
                    pos_years = 0
                    for y in range(2018, 2023):
                        yy = subset(d, pd.Timestamp(f"{y}-01-01", tz="UTC"), pd.Timestamp(f"{y+1}-01-01", tz="UTC"))
                        ym = metrics(yy); yearly[str(y)] = ym
                        if ym["E1"]["net_sum"] is not None and ym["E1"]["net_sum"] > 0:
                            pos_years += 1
                    if m["n"] >= 80 and m["E1"]["mean"] > 0 and m["STRESS"]["mean"] > 0 and pos_years >= 4 and m["E1"]["p"] < 0.01:
                        discovery.append({"candidate_id": cid, "rule": rule, "discovery": m, "discovery_yearly": yearly, "positive_discovery_years": pos_years})
                    done += 1; heartbeat(progress, done, 54, "discovery_2018_2022", {"discovery_candidates": len(discovery)})

    discovery_ids = sorted(x["candidate_id"] for x in discovery)
    discovery_hash = hashlib.sha256("|".join(discovery_ids).encode()).hexdigest()
    heartbeat(progress, 54, 54, "discovery_frozen_before_confirmation", {"count": len(discovery), "sha256": discovery_hash})

    confirmed = []
    pvals = []
    temp = []
    for c in discovery:
        r = c["rule"]; trades = simulate(df, zscores[r["lookback_hours"]], r["entry_abs_z"], r["exit_abs_z"], r["max_hold_hours"])
        cc = subset(trades, DISC_END, CONF_END); cm = metrics(cc)
        y23 = metrics(subset(cc, pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")))
        y24 = metrics(subset(cc, pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")))
        temp.append((c, cm, y23, y24)); pvals.append(cm["E1"]["p"] if cm["n"] else 1.0)
    qvals = bh_qvalues(pvals)
    for idx, (c, cm, y23, y24) in enumerate(temp):
        q = qvals[idx]
        if cm["n"] >= 30 and cm["E1"]["mean"] > 0 and cm["STRESS"]["mean"] > 0 and y23["E1"]["net_sum"] > 0 and y24["E1"]["net_sum"] > 0 and q <= 0.05:
            x = dict(c); x["confirmation"] = cm; x["confirmation_2023"] = y23; x["confirmation_2024"] = y24; x["confirmation_bh_q"] = q; confirmed.append(x)
    confirm_ids = sorted(x["candidate_id"] for x in confirmed)
    confirm_hash = hashlib.sha256("|".join(confirm_ids).encode()).hexdigest()
    heartbeat(progress, 54, 54, "confirmation_frozen_before_2025", {"count": len(confirmed), "sha256": confirm_hash})

    survivors = []
    diagnostics = []
    for c in confirmed:
        r = c["rule"]; trades = simulate(df, zscores[r["lookback_hours"]], r["entry_abs_z"], r["exit_abs_z"], r["max_hold_hours"])
        yy = subset(trades, CONF_END, PREOOS_END); ym = metrics(yy)
        h1 = metrics(subset(yy, pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2025-07-01", tz="UTC")))
        h2 = metrics(subset(yy, pd.Timestamp("2025-07-01", tz="UTC"), PREOOS_END))
        stress_vals = [t["STRESS"] for t in yy]
        ex_best = list(stress_vals)
        if ex_best:
            ex_best.pop(int(np.argmax(ex_best)))
        ex_best_sum = float(np.sum(ex_best)) if ex_best else None
        positive_gross = [max(0.0, t["STRESS"]) for t in yy]
        pos_sum = float(np.sum(positive_gross))
        top_share = (max(positive_gross) / pos_sum) if pos_sum > 0 and positive_gross else None
        passed = bool(
            ym["n"] >= 15 and ym["E1"]["mean"] > 0 and ym["STRESS"]["mean"] > 0 and
            h1["E1"]["net_sum"] is not None and h1["E1"]["net_sum"] > 0 and
            h2["E1"]["net_sum"] is not None and h2["E1"]["net_sum"] > 0 and
            ex_best_sum is not None and ex_best_sum > 0 and (top_share is None or top_share <= 0.35)
        )
        d = dict(c); d["pre_oos_2025"] = ym; d["pre_oos_2025_h1"] = h1; d["pre_oos_2025_h2"] = h2; d["stress_ex_best_net_sum"] = ex_best_sum; d["stress_top_positive_trade_share"] = top_share; d["passed_pre_oos"] = passed
        diagnostics.append(d)
        if passed:
            survivors.append(d)

    result = {
        "schema": 1, "method": "btc_eth_relative_value_mean_reversion", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": "research/autonomous/R8_BTC_ETH_RELATIVE_VALUE_PREREGISTRATION_2026_09_12.md",
        "protected_2026_opened": False, "input_sha256": input_hashes, "definitions_tested": 54,
        "discovery_candidate_count": len(discovery), "discovery_frozen_ids_sha256": discovery_hash,
        "confirmation_candidate_count": len(confirmed), "confirmation_frozen_ids_sha256": confirm_hash,
        "survivor_count": len(survivors), "survivors": survivors, "diagnostics": diagnostics,
    }
    result_path = out / "r8_btc_eth_relative_value_result.json"; atomic_json(result_path, result)
    csv_path = out / "r8_btc_eth_relative_value_survivors.csv"
    pd.json_normalize(survivors).to_csv(csv_path, index=False) if survivors else pd.DataFrame().to_csv(csv_path, index=False)
    heartbeat(progress, 54, 54, "complete", {"discovery_candidates": len(discovery), "confirmation_candidates": len(confirmed), "survivors": len(survivors)})
    status = "PASS" if survivors else "FAIL"
    summary = f"R8 BTC/ETH relative-value {status}: {len(survivors)} pre-OOS survivors after frozen 2018-22 discovery, 2023-24 confirmation and 2025 gate; 2026 untouched."
    publish(args.publisher, status, summary, [result_path, csv_path])
    print(json.dumps({"status": status, "survivors": len(survivors), "protected_2026_opened": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
