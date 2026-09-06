#!/usr/bin/env python3
"""
D035-E1 — causal dual-source exploratory diagnostic.

IMPORTANT SCIENTIFIC STATUS
---------------------------
This is NOT a confirmation and cannot rescue the rejected D035 primary campaign.
It is an exploratory follow-up on the already-inspected 2024-2025 development sample.

Motivation:
The D035 v1.01 merged label BTCUSD+ETHUSD was assigned to the FIRST source event
even when the second source event arrived up to five minutes later. Therefore
filtering that label at the first timestamp would be look-ahead contaminated.

E1 fixes only that causal-timing problem:
- retain the frozen D035 BTC/ETH shock definitions;
- retain the frozen 30-minute per-source cooldown;
- require both BTC and ETH shocks within five minutes;
- signal timestamp = the LATER/SECOND qualifying source shock;
- primary cross-asset target = XLMUSD, frozen before this E1 run;
- all other available CFDs are diagnostics only;
- horizons remain +1/+5/+15/+30/+60/+120m;
- no 2026 data is touched.

Advance-to-confirmation gate for XLMUSD:
G1 >= 200 causal dual-source events with executable +15m response
G2 mean executable SHORT +15m >= +15 bps
G3 median executable SHORT +15m > 0
G4 day-cluster bootstrap 95% lower bound of raw executable +15m > 0
G5 mean event-minus-causal-control +15m >= +10 bps
G6 day-cluster bootstrap 95% lower bound of +15m differential > 0
G7 mean executable SHORT +30m > 0
G8 both 2024 and 2025 mean executable SHORT +15m > 0

Only 8/8 permits a fresh preregistration before touching 2026-H1.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import D035_Binance_Deleveraging_LeadLag_v1_01 as base
except ImportError as exc:
    raise SystemExit(
        "E1 requires D035_Binance_Deleveraging_LeadLag_v1_01.py in the SAME folder."
    ) from exc

EXPERIMENT = "D035_E1_CAUSAL_DUAL_SOURCE_CONFIRMATION_DIAGNOSTIC"
PRIMARY_TARGET = "XLMUSD"
SAMPLE_START = pd.Timestamp("2024-01-01T00:00:00Z")
SAMPLE_END = pd.Timestamp("2025-12-31T23:59:59Z")
WARMUP_START = pd.Timestamp("2023-11-01T00:00:00Z")
DUAL_WINDOW_MIN = 5
HORIZONS = (1, 5, 15, 30, 60, 120)


def log(msg: str) -> None:
    print(f"[D035-E1] {msg}", flush=True)


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


def bootstrap_day_mean(df: pd.DataFrame, col: str, reps: int = 20000, seed: int = 35101):
    z = df.dropna(subset=[col]).copy()
    if z.empty:
        return (np.nan, np.nan)
    z["day"] = z["event_time_utc"].dt.floor("D")
    groups = [g[col].to_numpy(float) for _, g in z.groupby("day")]
    if len(groups) < 10:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    vals = np.empty(reps, dtype=float)
    n = len(groups)
    for i in range(reps):
        picks = rng.integers(0, n, size=n)
        vals[i] = np.concatenate([groups[j] for j in picks]).mean()
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def format_eta(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        return "?"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def build_returns_with_progress(events, targets, control_events, out_dir):
    rows = []
    event_ns = base.build_event_exclusion_intervals(control_events)
    total = len(events) * len(targets)
    done = 0
    started = time.monotonic()
    last_print = 0.0

    for ti, (target, x0) in enumerate(sorted(targets.items()), start=1):
        canonical = base.canonical_cfd_symbol(target)
        x = x0.reset_index(drop=True)
        target_rows = []
        log(f"Target {ti}/{len(targets)} {target}: {len(events)} causal events")

        for ei, (_, e) in enumerate(events.iterrows(), start=1):
            ts = e["event_time_utc"]
            ent = base.first_row_at_or_after(x, ts, tolerance_min=2)
            if ent is not None:
                entry_mid = float(ent["mid_first"])
                if entry_mid > 0:
                    row = {
                        "experiment": EXPERIMENT,
                        "event_time_utc": ts,
                        "first_source_time_utc": e["first_source_time_utc"],
                        "confirmation_delay_min": float(e["confirmation_delay_min"]),
                        "sources": "BTCUSD+ETHUSD",
                        "source_count": 2,
                        "source_ret5_pct": float(e["ret5_pct"]),
                        "source_oi_chg5_pct": float(e["oi_chg5_pct"]),
                        "target_symbol": target,
                        "target_canonical": canonical,
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
                    target_rows.append(row)
                    rows.append(row)

            done += 1
            now = time.monotonic()
            if now - last_print >= 15 or done == total:
                elapsed = now - started
                rate = done / elapsed if elapsed > 0 else 0.0
                eta = (total - done) / rate if rate > 0 else float("nan")
                pct = 100.0 * done / total if total else 100.0
                log(f"progress {done}/{total} ({pct:.1f}%) | {target} event {ei}/{len(events)} | elapsed {format_eta(elapsed)} | ETA {format_eta(eta)}")
                last_print = now

        if target_rows:
            pd.DataFrame(target_rows).to_csv(out_dir / f"CHECKPOINT_{target}.csv", index=False)
            log(f"checkpoint saved: {target}")

    return pd.DataFrame(rows)


def summarize_target(g: pd.DataFrame) -> dict:
    out = {
        "target_symbol": str(g["target_symbol"].iloc[0]),
        "n": int(g["exec_short_15m_bps"].notna().sum()),
        "mean_entry_spread_bps": float(g["entry_spread_bps"].mean()),
        "mean_control_15m_bps": float(g["control_15m_bps"].mean()),
        "mean_diff_15m_bps": float(g["diff_15m_bps"].mean()),
        "median_exec_15m_bps": float(g["exec_short_15m_bps"].median()),
    }
    for h in HORIZONS:
        out[f"mean_exec_{h}m_bps"] = float(g[f"exec_short_{h}m_bps"].mean())
        out[f"median_exec_{h}m_bps"] = float(g[f"exec_short_{h}m_bps"].median())
    raw_ci = bootstrap_day_mean(g, "exec_short_15m_bps")
    diff_ci = bootstrap_day_mean(g, "diff_15m_bps")
    out["bootstrap_raw15_lo"] = raw_ci[0]
    out["bootstrap_raw15_hi"] = raw_ci[1]
    out["bootstrap_diff15_lo"] = diff_ci[0]
    out["bootstrap_diff15_hi"] = diff_ci[1]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfd-dir", required=True, type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("D035_E1_output"))
    ap.add_argument("--cache-dir", type=Path, default=Path("D035_binance_cache"))
    ap.add_argument("--server-utc-offset", type=int, default=None)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    log("EXPLORATORY DEVELOPMENT ONLY: 2024-2025. 2026 remains untouched.")
    log("Causal dual confirmation: tradable timestamp = SECOND source shock.")

    source5 = {}
    klines_1m = {}
    download_end = SAMPLE_END + pd.Timedelta(days=1)

    for sym in base.SOURCE_SYMBOLS:
        log(f"Loading cached Binance Vision {sym} OI metrics...")
        m, _ = base.load_metrics(args.cache_dir, sym, WARMUP_START, download_end)
        log(f"Loading cached Binance Vision {sym} 1m klines...")
        k, _ = base.load_klines(args.cache_dir, sym, WARMUP_START, download_end)
        klines_1m[sym] = k
        source5[sym] = base.exact_5m_source(k, m)

    btc_ev = base.causal_shocks(source5["BTCUSDT"], "BTCUSDT")
    eth_ev = base.causal_shocks(source5["ETHUSDT"], "ETHUSDT")
    all_events = base.merge_source_events(btc_ev, eth_ev)
    dual = build_causal_dual_events(btc_ev, eth_ev)
    dual = dual[(dual["event_time_utc"] >= SAMPLE_START) & (dual["event_time_utc"] <= SAMPLE_END)].copy()
    log(f"Causal dual-source events in sample: {len(dual)}")
    if dual.empty:
        raise RuntimeError("No causal dual-source events found.")

    cfd = base.load_cfd_files(args.cfd_dir)
    btc_key = next((k for k in cfd if base.canonical_cfd_symbol(k) == "BTCUSD"), None)
    if btc_key is None and args.server_utc_offset is None:
        raise RuntimeError("BTCUSD CFD export required for mechanical server->UTC alignment.")

    btc_for_cal = cfd[btc_key] if btc_key is not None else next(iter(cfd.values()))
    offset_qa = base.calibrate_offsets(btc_for_cal, klines_1m["BTCUSDT"], fixed_offset=args.server_utc_offset)
    offset_qa.to_csv(args.out_dir / "D035_E1_OFFSET_QA.csv", index=False)
    usable = int(offset_qa["usable"].sum())
    log(f"UTC alignment usable weeks: {usable}/{len(offset_qa)}")
    if usable < max(4, int(0.70 * len(offset_qa))):
        raise RuntimeError("UTC alignment QA failed.")

    aligned = {}
    for sym, df in cfd.items():
        x = base.apply_offsets(df, offset_qa)
        x = x[(x["utc_ts"] >= SAMPLE_START - pd.Timedelta(days=base.CONTROL_LOOKBACK_DAYS)) & (x["utc_ts"] <= SAMPLE_END + pd.Timedelta(hours=3))].copy()
        aligned[sym] = x
        log(f"Aligned {sym}: {len(x)} M1 rows")

    er = build_returns_with_progress(dual, aligned, control_events=all_events, out_dir=args.out_dir)
    dual.to_csv(args.out_dir / "D035_E1_CAUSAL_DUAL_EVENTS.csv", index=False)
    er.to_csv(args.out_dir / "D035_E1_EVENT_TARGET_RETURNS.csv", index=False)

    summary_rows = [summarize_target(g) for _, g in er.groupby("target_symbol")]
    summary = pd.DataFrame(summary_rows).sort_values("mean_exec_15m_bps", ascending=False)
    summary.to_csv(args.out_dir / "D035_E1_SUMMARY_BY_TARGET.csv", index=False)

    primary = er[er["target_symbol"].str.upper() == PRIMARY_TARGET].copy()
    if primary.empty:
        verdict = {"experiment": EXPERIMENT, "primary_target": PRIMARY_TARGET, "verdict": "E1_INVALID_PRIMARY_TARGET_MISSING", "gates": {}}
    else:
        p = summarize_target(primary)
        primary["year"] = primary["event_time_utc"].dt.year
        y = primary.groupby("year")["exec_short_15m_bps"].mean().to_dict()
        gates = {
            "G1_n_ge200": p["n"] >= 200,
            "G2_mean_exec15_ge15bps": p["mean_exec_15m_bps"] >= 15.0,
            "G3_median_exec15_gt0": p["median_exec_15m_bps"] > 0.0,
            "G4_bootstrap_raw15_lower_gt0": p["bootstrap_raw15_lo"] > 0.0,
            "G5_mean_diff15_ge10bps": p["mean_diff_15m_bps"] >= 10.0,
            "G6_bootstrap_diff15_lower_gt0": p["bootstrap_diff15_lo"] > 0.0,
            "G7_mean_exec30_gt0": p["mean_exec_30m_bps"] > 0.0,
            "G8_2024_and_2025_exec15_positive": float(y.get(2024, np.nan)) > 0.0 and float(y.get(2025, np.nan)) > 0.0,
        }
        verdict = {
            "experiment": EXPERIMENT,
            "scientific_status": "EXPLORATORY_SAME_SAMPLE_NOT_CONFIRMATION",
            "primary_target": PRIMARY_TARGET,
            "causal_rule": "BTC and ETH frozen D035 shocks within 5m; signal at later/second shock",
            "causal_dual_events": int(len(dual)),
            "primary": p,
            "year_mean_exec15_bps": {str(k): float(v) for k, v in y.items()},
            "gates": gates,
            "gate_pass_count": int(sum(bool(v) for v in gates.values())),
            "verdict": "E1_ADVANCE_TO_FRESH_2026_PREREGISTRATION" if all(gates.values()) else "E1_DO_NOT_ADVANCE",
            "confirmation_2026_touched": False,
        }

    (args.out_dir / "D035_E1_VERDICT.json").write_text(json.dumps(verdict, indent=2, default=str) + "\n", encoding="utf-8")
    report = [
        "# D035-E1 causal dual-source diagnostic", "",
        f"Status: **{verdict['verdict']}**", "",
        "Scientific status: exploratory same-sample follow-up; not confirmation; cannot rescue D035 primary.", "",
        f"Causal dual events: **{len(dual)}**", f"Primary target: **{PRIMARY_TARGET}**", "",
    ]
    if verdict.get("gates"):
        report += ["## Gates", ""]
        for k, v in verdict["gates"].items():
            report.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
        report += ["", f"Pass count: **{verdict['gate_pass_count']}/8**", ""]
    report += ["## Per-target diagnostics", "", "```csv", summary.to_csv(index=False).strip(), "```", "", "2026-H1 was not touched."]
    (args.out_dir / "D035_E1_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    log(f"VERDICT {verdict['verdict']} — {verdict.get('gate_pass_count', 0)}/8")
    log(f"Output: {args.out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
