#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6


START = pd.Timestamp("2026-01-01T00:00:00Z")
SPLIT = pd.Timestamp("2026-05-01T00:00:00Z")
END = pd.Timestamp("2026-09-01T00:00:00Z")
JAN7 = pd.Timestamp("2026-01-07T00:00:00Z")
AUG25 = pd.Timestamp("2026-08-25T00:00:00Z")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def heartbeat(path: Path | None, completed: int, total: int, stage: str, extra=None) -> None:
    if not path:
        return
    obj = {
        "completed": int(completed),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        obj.update(extra)
    atomic_json(path, obj)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"manifest missing: {path}")
    out = {}
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def candidate_fingerprint(rules) -> str:
    payload = [
        {
            k: r[k]
            for k in (
                "candidate_id",
                "lookback_bars",
                "buffer_atr",
                "horizon_bars",
                "session",
                "session_start",
                "session_end",
                "direction_name",
                "direction",
            )
        }
        for r in rules
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_manifest(path: Path, timeframe: str, prereg: dict) -> dict:
    md = parse_manifest(path)
    expected = {
        "symbol": "XAUUSD",
        "period": timeframe.upper(),
        "from": "2026.01.01 00:00:00",
        "to_exclusive": "2026.09.01 00:00:00",
        "server": prereg["inputs"]["required_server"],
    }
    for k, v in expected.items():
        if md.get(k) != v:
            raise RuntimeError(f"{timeframe} manifest mismatch {k}: {md.get(k)!r} != {v!r}")
    if md.get("terminal_data_path", "").lower() != prereg["inputs"]["required_terminal_data_path"].lower():
        raise RuntimeError(f"{timeframe} manifest terminal_data_path mismatch")
    return md


def load_snapshot(path: Path, timeframe: str) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"{timeframe} snapshot missing: {path}")
    df = pd.read_csv(path)
    req = {"server_epoch", "open", "high", "low", "close"}
    if not req.issubset(df.columns):
        raise RuntimeError(f"{timeframe} snapshot columns invalid: {sorted(df.columns)}")
    epoch = pd.to_numeric(df["server_epoch"], errors="raise").astype("int64")
    step = 60 if timeframe.upper() == "M1" else 300
    if (epoch % step != 0).any():
        raise RuntimeError(f"{timeframe} timestamp alignment failure")
    t = pd.to_datetime(epoch, unit="s", utc=True)
    z = pd.DataFrame(
        {
            "time": t,
            "open": pd.to_numeric(df["open"], errors="raise"),
            "high": pd.to_numeric(df["high"], errors="raise"),
            "low": pd.to_numeric(df["low"], errors="raise"),
            "close": pd.to_numeric(df["close"], errors="raise"),
        }
    )
    if "tick_volume" in df.columns:
        z["volume"] = pd.to_numeric(df["tick_volume"], errors="coerce")
    if len(z) == 0:
        raise RuntimeError(f"{timeframe} snapshot empty")
    if not z["time"].is_monotonic_increasing or z["time"].duplicated().any():
        raise RuntimeError(f"{timeframe} timestamps not strictly increasing/unique")
    if (z.time < START).any() or (z.time >= END).any():
        raise RuntimeError(f"{timeframe} snapshot contains rows outside frozen Jan-Aug 2026 window")
    minimum_rows = 150000 if timeframe.upper() == "M1" else 30000
    if len(z) < minimum_rows:
        raise RuntimeError(f"{timeframe} snapshot too short: {len(z)} < {minimum_rows}")
    if z.time.min() > JAN7 or z.time.max() < AUG25:
        raise RuntimeError(f"{timeframe} frozen-window temporal coverage incomplete: {z.time.min()} .. {z.time.max()}")
    return z.reset_index(drop=True)


def read_news_mask(path: Path, expected_sha256: str):
    if not path.exists():
        raise RuntimeError(f"frozen news mask missing: {path}")
    got = sha256_file(path)
    if got != expected_sha256:
        raise RuntimeError(f"frozen news mask hash mismatch: {got}")
    m = pd.read_csv(path)
    req = {"mask_start_server_epoch", "mask_end_server_epoch"}
    if not req.issubset(m.columns):
        raise RuntimeError("frozen news mask columns invalid")
    intervals = sorted((int(a), int(b)) for a, b in zip(m.mask_start_server_epoch, m.mask_end_server_epoch))
    return intervals, got


def apply_news_mask(source: pd.DataFrame, intervals) -> pd.DataFrame:
    epochs = (source.time.astype("int64") // 1_000_000_000).to_numpy(dtype=np.int64)
    keep = np.ones(len(source), dtype=bool)
    j = 0
    for i, t in enumerate(epochs):
        while j < len(intervals) and intervals[j][1] < t:
            j += 1
        if j < len(intervals) and intervals[j][0] <= t <= intervals[j][1]:
            keep[i] = False
    out = source.loc[keep].reset_index(drop=True)
    if len(out) < 30000:
        raise RuntimeError(f"news-clean M5 snapshot too short: {len(out)}")
    return out


def temporal_halves(trades):
    h1 = [t for t in trades if START <= pd.Timestamp(t["entry_time"]) < SPLIT and pd.Timestamp(t["exit_time"]) < SPLIT]
    h2 = [t for t in trades if SPLIT <= pd.Timestamp(t["entry_time"]) < END and pd.Timestamp(t["exit_time"]) < END]
    return h1, h2


def publish(publisher: str | None, status: str, summary: str, artifacts) -> None:
    if not publisher:
        return
    cmd = ["python", publisher, "--phase", "r6-protected-2026-oos", "--status", status, "--summary", summary]
    for artifact in artifacts:
        cmd += ["--artifact", str(artifact)]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--r6-result", required=True)
    ap.add_argument("--preregistration", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    ap.add_argument("--root")
    args = ap.parse_args()

    prereg_path = Path(args.preregistration)
    prereg = load_json(prereg_path)
    result = load_json(Path(args.r6_result))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None

    if prereg.get("authorized_by_human") is not True:
        raise RuntimeError("protected 2026 OOS not human-authorized")
    if prereg.get("retuning_allowed") is not False:
        raise RuntimeError("preregistration must forbid retuning")
    if prereg.get("scientific_evaluation_before_amendment") is not False:
        raise RuntimeError("invalid transport amendment provenance")
    survivors = result.get("survivors") or []
    if len(survivors) != 12 or int(result.get("survivor_count", -1)) != 12:
        raise RuntimeError("expected exactly 12 frozen R6 survivors")

    root_value = args.root or ""
    def expand(value: str) -> Path:
        return Path(value.replace("{ROOT}", root_value)) if "{ROOT}" in value else Path(value)

    inputs = prereg["inputs"]
    m5_path = expand(inputs["m5_csv"])
    m1_path = expand(inputs["m1_csv"])
    m5_manifest_path = expand(inputs["m5_manifest"])
    m1_manifest_path = expand(inputs["m1_manifest"])
    mask_path = expand(inputs["news_mask"])

    frozen_fp = candidate_fingerprint(survivors)
    heartbeat(progress, 0, 12, "validate_frozen_inputs", {"frozen_candidates_sha256": frozen_fp})
    m5_manifest = validate_manifest(m5_manifest_path, "M5", prereg)
    m1_manifest = validate_manifest(m1_manifest_path, "M1", prereg)
    raw_m5 = load_snapshot(m5_path, "M5")
    raw_m1 = load_snapshot(m1_path, "M1")
    intervals, mask_sha = read_news_mask(mask_path, inputs["news_mask_expected_sha256"])
    source = apply_news_mask(raw_m5, intervals)
    raw = raw_m1

    start = max(source.time.min(), raw.time.min())
    end = min(source.time.max(), raw.time.max())
    overlap_days = float((end - start).total_seconds() / 86400.0)
    if overlap_days < float(prereg["oos_window"]["minimum_overlap_days"]):
        raise RuntimeError(f"insufficient Jan-Aug 2026 overlap: {overlap_days:.2f}d")
    if start > JAN7 or end < AUG25:
        raise RuntimeError(f"overlap temporal bounds incomplete: {start} .. {end}")

    source = source[(source.time >= start) & (source.time <= end)].reset_index(drop=True)
    raw = raw[(raw.time >= start) & (raw.time <= end)].reset_index(drop=True)

    input_manifest = {
        "m5": {
            "path": str(m5_path),
            "sha256": sha256_file(m5_path),
            "rows_raw": int(len(raw_m5)),
            "rows_news_clean": int(len(source)),
            "manifest_path": str(m5_manifest_path),
            "manifest_sha256": sha256_file(m5_manifest_path),
            "manifest": m5_manifest,
        },
        "m1": {
            "path": str(m1_path),
            "sha256": sha256_file(m1_path),
            "rows": int(len(raw_m1)),
            "manifest_path": str(m1_manifest_path),
            "manifest_sha256": sha256_file(m1_manifest_path),
            "manifest": m1_manifest,
        },
        "news_mask": {
            "path": str(mask_path),
            "sha256": mask_sha,
            "intervals": len(intervals),
        },
    }

    records = []
    pvals = []
    for i, rule in enumerate(survivors, 1):
        ledger, accounting, full = r6.evaluate_year(rule, source, raw, 2026)
        h1, h2 = temporal_halves(ledger)
        h1_stats = {p: econ.stats(h1, p) for p in econ.PROFILES}
        h2_stats = {p: econ.stats(h2, p) for p in econ.PROFILES}
        boot = r6.day_block_bootstrap(ledger, "E1", rule["candidate_id"])
        rec = {
            "candidate_id": rule["candidate_id"],
            "definition": {
                k: rule[k]
                for k in (
                    "lookback_bars",
                    "buffer_atr",
                    "horizon_bars",
                    "session",
                    "session_start",
                    "session_end",
                    "direction_name",
                    "direction",
                )
            },
            "signal_accounting_2026_jan_aug": accounting,
            "oos_full": full,
            "oos_half1_jan_apr": h1_stats,
            "oos_half2_may_aug": h2_stats,
            "bootstrap_2026_e1": boot,
        }
        records.append(rec)
        pvals.append(float(boot["p_one_sided"]))
        heartbeat(progress, i, 12, "evaluate_frozen_2026_jan_aug", {"candidate_id": rule["candidate_id"]})

    qvals = r6.bh_qvalues(pvals)
    gates = prereg["candidate_pass_criteria"]
    passed = []
    for rec, q in zip(records, qvals):
        rec["bh_fdr_q"] = float(q)
        full = rec["oos_full"]
        h1 = rec["oos_half1_jan_apr"]
        h2 = rec["oos_half2_may_aug"]
        boot = rec["bootstrap_2026_e1"]
        ok = (
            full["E1"]["trades"] >= int(gates["minimum_full_oos_trades"])
            and h1["E1"]["trades"] >= int(gates["minimum_each_temporal_half_trades"])
            and h2["E1"]["trades"] >= int(gates["minimum_each_temporal_half_trades"])
            and full["E1"]["net"] > float(gates["full_e1_net_gt"])
            and full["STRESS"]["net"] > float(gates["full_stress_net_gt"])
            and h1["E1"]["net"] > float(gates["half1_e1_net_gt"])
            and h2["E1"]["net"] > float(gates["half2_e1_net_gt"])
            and h1["STRESS"]["net"] > float(gates["half1_stress_net_gt"])
            and h2["STRESS"]["net"] > float(gates["half2_stress_net_gt"])
            and r6.pf(full["E1"]) > float(gates["full_e1_profit_factor_gt"])
            and full["E1"]["ex_best_positive_net"] > float(gates["full_e1_net_after_best_positive_trade_removed_gt"])
            and boot.get("p05") is not None
            and float(boot["p05"]) > float(gates["day_block_bootstrap_e1_p05_gt"])
            and float(q) <= float(gates["bh_fdr_q_lte"])
        )
        rec["oos_pass"] = bool(ok)
        if ok:
            passed.append(rec["candidate_id"])

    status = "PASS" if passed else "FAIL"
    report = {
        "schema": 2,
        "phase": "r6-protected-2026-oos",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "protected_2026_opened": True,
        "evaluated_window": {"start": START.isoformat(), "split": SPLIT.isoformat(), "end_exclusive": END.isoformat()},
        "human_authorized": True,
        "retuning_performed": False,
        "frozen_candidate_count": 12,
        "frozen_candidates_sha256": frozen_fp,
        "input_manifest": input_manifest,
        "coverage": {"start_utc": start.isoformat(), "end_utc": end.isoformat(), "days": overlap_days},
        "pass_count": len(passed),
        "passing_candidate_ids": passed,
        "candidates": records,
        "interpretation": "PASS identifies post-cost protected-OOS EA-candidate evidence only. No live deployment authorization is implied. FAIL closes this frozen R6 family for promotion; no retuning on 2026 is allowed.",
    }
    report_path = out / "r6_protected_2026_oos_result.json"
    atomic_json(report_path, report)
    heartbeat(progress, 12, 12, "complete", {"status": status, "pass_count": len(passed)})
    summary = f"R6 protected Jan-Aug 2026 OOS {status}: {len(passed)}/12 frozen candidates pass all preregistered post-cost gates; no retuning."
    publish(args.publisher, status, summary, [report_path, prereg_path])
    print(json.dumps({"status": status, "pass_count": len(passed), "passing_candidate_ids": passed, "protected_2026_opened": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
