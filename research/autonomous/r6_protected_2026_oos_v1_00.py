#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import strategy_factory_causal_next_open_v1_00 as r5
import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


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


def select_input(root: Path, timeframe: str) -> Path:
    tf = timeframe.lower()
    hits = []
    for p in root.rglob("*.csv"):
        name = p.name.lower()
        if "xauusd" in name and "2026" in name and tf in name:
            hits.append(p)
    hits = sorted(set(hits))
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one XAUUSD 2026 {timeframe} CSV under {root}, found {len(hits)}: {[str(x) for x in hits]}")
    return hits[0]


def load_market_2026(path: Path):
    meta = r5.detect(path)
    if not meta:
        raise RuntimeError(f"unreadable OHLC input: {path}")
    df = r5.load_market(path, meta, 4_000_000)
    if len(df) == 0:
        raise RuntimeError(f"empty input: {path}")
    y = df[df.time.dt.year == 2026].reset_index(drop=True).copy()
    if len(y) == 0:
        raise RuntimeError(f"no 2026 rows in {path}")
    if (y.time < pd.Timestamp("2026-01-01", tz="UTC")).any() or (y.time >= pd.Timestamp("2027-01-01", tz="UTC")).any():
        raise RuntimeError("year filter invariant failed")
    return y


def stats(trades, profile):
    return econ.stats(trades, profile)


def temporal_halves(trades, start: pd.Timestamp, end: pd.Timestamp):
    mid = start + (end - start) / 2
    a = [t for t in trades if start <= pd.Timestamp(t["entry_time"]) < mid and pd.Timestamp(t["exit_time"]) < mid]
    b = [t for t in trades if mid <= pd.Timestamp(t["entry_time"]) < end and pd.Timestamp(t["exit_time"]) < end]
    return a, b, mid


def publish(publisher: str | None, status: str, summary: str, artifacts) -> None:
    if not publisher:
        return
    cmd = ["python", publisher, "--phase", "r6-protected-2026-oos", "--status", status, "--summary", summary]
    for a in artifacts:
        cmd += ["--artifact", str(a)]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root", required=True)
    ap.add_argument("--r6-result", required=True)
    ap.add_argument("--preregistration", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()

    root = Path(args.phase_ib_root)
    result = load_json(Path(args.r6_result))
    prereg = load_json(Path(args.preregistration))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None

    if prereg.get("authorized_by_human") is not True:
        raise RuntimeError("protected 2026 OOS not human-authorized in preregistration")
    if prereg.get("retuning_allowed") is not False:
        raise RuntimeError("preregistration must forbid retuning")
    survivors = result.get("survivors") or []
    if len(survivors) != 12 or int(result.get("survivor_count", -1)) != 12:
        raise RuntimeError("expected exactly 12 frozen R6 survivors")

    frozen_fp = candidate_fingerprint(survivors)
    heartbeat(progress, 0, 12, "select_oos_inputs", {"frozen_candidates_sha256": frozen_fp})
    m5_path = select_input(root, "m5")
    m1_path = select_input(root, "m1")

    input_manifest = {
        "m5": {"path": str(m5_path), "sha256": sha256_file(m5_path)},
        "m1": {"path": str(m1_path), "sha256": sha256_file(m1_path)},
    }
    heartbeat(progress, 0, 12, "load_protected_2026", {"input_manifest": input_manifest})
    source = load_market_2026(m5_path)
    raw = load_market_2026(m1_path)

    start = max(source.time.min(), raw.time.min())
    end = min(source.time.max(), raw.time.max())
    coverage_days = float((end - start).total_seconds() / 86400.0)
    min_cov = float(prereg["oos_window"]["minimum_coverage_days"])
    if coverage_days < min_cov:
        raise RuntimeError(f"insufficient 2026 overlap coverage: {coverage_days:.2f}d < {min_cov:.2f}d")

    source = source[(source.time >= start) & (source.time <= end)].reset_index(drop=True)
    raw = raw[(raw.time >= start) & (raw.time <= end)].reset_index(drop=True)

    records = []
    pvals = []
    for i, rule in enumerate(survivors, 1):
        ledger, accounting, full = r6.evaluate_year(rule, source, raw, 2026)
        h1, h2, midpoint = temporal_halves(ledger, start, end)
        m1 = {p: stats(h1, p) for p in econ.PROFILES}
        m2 = {p: stats(h2, p) for p in econ.PROFILES}
        boot = r6.day_block_bootstrap(ledger, "E1", rule["candidate_id"])
        rec = {
            "candidate_id": rule["candidate_id"],
            "definition": {k: rule[k] for k in ("lookback_bars", "buffer_atr", "horizon_bars", "session", "session_start", "session_end", "direction_name", "direction")},
            "signal_accounting_2026": accounting,
            "oos_full": full,
            "oos_half1": m1,
            "oos_half2": m2,
            "bootstrap_2026_e1": boot,
            "midpoint_utc": midpoint.isoformat(),
        }
        records.append(rec)
        pvals.append(float(boot["p_one_sided"]))
        heartbeat(progress, i, 12, "evaluate_frozen_2026", {"candidate_id": rule["candidate_id"]})

    qvals = r6.bh_qvalues(pvals)
    passed = []
    gates = prereg["candidate_pass_criteria"]
    for rec, q in zip(records, qvals):
        rec["bh_fdr_q"] = float(q)
        f = rec["oos_full"]
        a = rec["oos_half1"]
        b = rec["oos_half2"]
        boot = rec["bootstrap_2026_e1"]
        ok = (
            f["E1"]["trades"] >= int(gates["minimum_full_oos_trades"])
            and a["E1"]["trades"] >= int(gates["minimum_each_temporal_half_trades"])
            and b["E1"]["trades"] >= int(gates["minimum_each_temporal_half_trades"])
            and f["E1"]["net"] > float(gates["full_e1_net_gt"])
            and f["STRESS"]["net"] > float(gates["full_stress_net_gt"])
            and a["E1"]["net"] > float(gates["half1_e1_net_gt"])
            and b["E1"]["net"] > float(gates["half2_e1_net_gt"])
            and a["STRESS"]["net"] > float(gates["half1_stress_net_gt"])
            and b["STRESS"]["net"] > float(gates["half2_stress_net_gt"])
            and r6.pf(f["E1"]) > float(gates["full_e1_profit_factor_gt"])
            and f["E1"]["ex_best_positive_net"] > float(gates["full_e1_net_after_best_positive_trade_removed_gt"])
            and boot.get("p05") is not None
            and float(boot["p05"]) > float(gates["day_block_bootstrap_e1_p05_gt"])
            and float(q) <= float(gates["bh_fdr_q_lte"])
        )
        rec["oos_pass"] = bool(ok)
        if ok:
            passed.append(rec["candidate_id"])

    status = "PASS" if passed else "FAIL"
    report = {
        "schema": 1,
        "phase": "r6-protected-2026-oos",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "protected_2026_opened": True,
        "human_authorized": True,
        "retuning_performed": False,
        "frozen_candidate_count": 12,
        "frozen_candidates_sha256": frozen_fp,
        "input_manifest": input_manifest,
        "coverage": {"start_utc": start.isoformat(), "end_utc": end.isoformat(), "days": coverage_days},
        "pass_count": len(passed),
        "passing_candidate_ids": passed,
        "candidates": records,
        "interpretation": "PASS identifies post-cost OOS EA candidate evidence only. No live deployment authorization is implied. FAIL closes this frozen R6 family for promotion; no retuning on 2026 is allowed."
    }
    report_path = out / "r6_protected_2026_oos_result.json"
    atomic_json(report_path, report)
    heartbeat(progress, 12, 12, "complete", {"status": status, "pass_count": len(passed)})
    summary = f"R6 protected 2026 OOS {status}: {len(passed)}/12 frozen candidates pass all preregistered post-cost gates; no retuning."
    publish(args.publisher, status, summary, [report_path, Path(args.preregistration)])
    print(json.dumps({"status": status, "pass_count": len(passed), "passing_candidate_ids": passed, "protected_2026_opened": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
