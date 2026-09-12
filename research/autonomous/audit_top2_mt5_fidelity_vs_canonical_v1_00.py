#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import r6_xau_low_turnover_breakout_v1_00 as r6

CANDIDATES = ("R6B-347", "R6B-307")
YEARS = (2024, 2025)


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_mt5(path: Path):
    z = pd.read_csv(path, sep=";")
    req = {"candidate_id", "entry_time", "exit_time"}
    if not req.issubset(z.columns):
        raise RuntimeError(f"bad MT5 trade csv: {path}")
    z["entry_time"] = pd.to_datetime(z["entry_time"], format="%Y.%m.%d %H:%M:%S", utc=True)
    z["exit_time"] = pd.to_datetime(z["exit_time"], format="%Y.%m.%d %H:%M:%S", utc=True)
    return z.sort_values(["entry_time", "exit_time"]).reset_index(drop=True)


def pairs_from_ledger(ledger):
    return [(pd.Timestamp(t["entry_time"]).tz_convert("UTC"), pd.Timestamp(t["exit_time"]).tz_convert("UTC")) for t in ledger]


def pairs_from_df(z):
    return list(zip(z["entry_time"], z["exit_time"]))


def compare_pairs(canonical, mt5):
    cset = set(canonical)
    mset = set(mt5)
    exact = len(cset & mset)
    centry = {a for a, _ in canonical}
    mentry = {a for a, _ in mt5}
    eexact = len(centry & mentry)
    return {
        "canonical_trades": len(canonical),
        "mt5_trades": len(mt5),
        "exact_entry_exit_matches": exact,
        "exact_entry_exit_match_fraction_of_canonical": exact / len(canonical) if canonical else 1.0,
        "exact_entry_matches": eexact,
        "exact_entry_match_fraction_of_canonical": eexact / len(centry) if centry else 1.0,
        "canonical_only_pairs": len(cset - mset),
        "mt5_only_pairs": len(mset - cset),
        "parity": bool(len(canonical) == len(mt5) and exact == len(canonical)),
    }


def publish(publisher, status, summary, artifacts):
    if not publisher:
        return
    cmd = ["python", publisher, "--phase", "top2-xau-mt5-fidelity-audit", "--status", status, "--summary", summary]
    for a in artifacts:
        cmd += ["--artifact", str(a)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root", required=True)
    ap.add_argument("--mt5-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--publisher")
    args = ap.parse_args()

    ib = Path(args.phase_ib_root)
    mt5dir = Path(args.mt5_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    source_all = r6.load_exact(ib / "xauusd_m5_2024_2025_news_clean.csv")
    raw_all = r6.load_exact(ib / "xauusd_m1_2024_2025_raw.csv")
    rules = {x["candidate_id"]: x for x in r6.definition_grid()}

    result = {
        "schema": 1,
        "phase": "top2-xau-mt5-fidelity-audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "question": "Does the completed MT5 tester reproduce the exact frozen canonical 2024/2025 R6 trade schedule?",
        "protected_2026_opened": False,
        "canonical_inputs": r6.EXPECTED,
        "candidates": {},
    }

    all_pass = True
    for cid in CANDIDATES:
        rule = rules[cid]
        mt5 = load_mt5(mt5dir / f"{cid}_TRADES.csv")
        rec = {
            "frozen_rule": {k: rule[k] for k in ("candidate_id", "lookback_bars", "buffer_atr", "horizon_bars", "session", "session_start", "session_end", "direction_name", "direction")},
            "years": {},
        }
        for year in YEARS:
            src = r6.year_slice(source_all, year)
            raw = r6.year_slice(raw_all, year)
            ledger, _, _ = r6.evaluate_year(rule, src, raw, year)
            canonical = pairs_from_ledger(ledger)
            mz = mt5[mt5.entry_time.dt.year == year]
            comp = compare_pairs(canonical, pairs_from_df(mz))
            rec["years"][str(year)] = comp
            all_pass = all_pass and comp["parity"]
        result["candidates"][cid] = rec

    result["scientific_status"] = "PASS_EXACT_PARITY" if all_pass else "FAIL_FIDELITY_MISMATCH"
    result["interpretation"] = (
        "PASS means the MT5 harness reproduced the exact canonical 2024/2025 entry/exit schedule."
        if all_pass else
        "FAIL means the completed MT5 long-history run is descriptive only and must not be used as execution-fidelity validation of the frozen R6 candidates. Repair the harness without changing the candidate definitions."
    )

    rp = out / "top2_mt5_fidelity_audit.json"
    atomic_json(rp, result)
    status = "PASS" if all_pass else "FAIL"
    summary = result["scientific_status"] + "; 2026 not opened by this audit."
    publish(args.publisher, status, summary, [rp])
    print(json.dumps({"status": status, "scientific_status": result["scientific_status"], "protected_2026_opened": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
