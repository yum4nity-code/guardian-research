#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PHASE_PUBLISH = "phase-id-xau-temporal-robustness"


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def heartbeat(path: Path | None, completed: int, total: int, stage: str) -> None:
    if path:
        atomic_json(path, {
            "completed": int(completed),
            "total": int(total),
            "stage": stage,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        })


def load_ic_module(path: Path):
    spec = importlib.util.spec_from_file_location("guardian_phase_ic", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Phase I-C engine: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def signed_effect_test(ic, values: np.ndarray, mask: np.ndarray, outcome: str):
    if outcome == "mean_fwd_ret_atr":
        return ic.continuous_test(values, mask)
    return ic.binary_test(values, mask)


def sign_of(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def publish(publisher: Path | None, status: str, summary: str, artifacts: list[Path], cwd: Path) -> None:
    if publisher is None:
        return
    cmd = [sys.executable, str(publisher), "--phase", PHASE_PUBLISH, "--status", status, "--summary", summary]
    for p in artifacts:
        if p.exists():
            cmd += ["--artifact", str(p)]
    cp = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"publication failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ib-dir", required=True)
    ap.add_argument("--ic-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--deploy", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()

    ib = Path(args.ib_dir)
    icdir = Path(args.ic_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    deploy = Path(args.deploy)
    hb = Path(args.progress_file) if args.progress_file else None
    publisher = Path(args.publisher) if args.publisher else None

    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    if policy.get("protected_2026_untouched") is not True:
        raise RuntimeError("policy does not explicitly seal 2026")

    ib_integrity = json.loads((ib / "phase_ib_integrity.json").read_text(encoding="utf-8"))
    ib_summary = json.loads((ib / "phase_ib_summary.json").read_text(encoding="utf-8"))
    ic_summary = json.loads((icdir / "phase_ic_summary.json").read_text(encoding="utf-8"))
    survivors_path = icdir / "phase_ic_survivors.csv"
    cutpoints_path = icdir / "phase_ic_frozen_2024_cutpoints.json"
    data_path = ib / "xauusd_m5_2024_2025_news_clean.csv"
    ic_engine = deploy / "research" / "autonomous" / "phase_ic_xau_phenomenon_atlas_v1_00.py"

    for p in (survivors_path, cutpoints_path, data_path, ic_engine):
        if not p.exists():
            raise RuntimeError(f"missing required artifact: {p}")
    if ib_integrity.get("status") != "PASS" or ib_integrity.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-B integrity/provenance is not PASS with 2026 sealed")
    if ib_summary.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-B summary does not seal 2026")
    if ic_summary.get("technical_status") != "PASS" or ic_summary.get("scientific_status") != "SURVIVORS_FOUND":
        raise RuntimeError("Phase I-C terminal survivor result is required")
    if ic_summary.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-C provenance does not seal 2026")

    heartbeat(hb, 0, 100, "load")
    candidates = pd.read_csv(survivors_path)
    if len(candidates) != int(ic_summary.get("confirmation_survivors", -1)):
        raise RuntimeError(f"Phase I-C survivor count mismatch csv={len(candidates)} summary={ic_summary.get('confirmation_survivors')}")
    cuts = json.loads(cutpoints_path.read_text(encoding="utf-8"))
    df = pd.read_csv(data_path)
    if not df["server_time"].astype(str).str.startswith(("2024.", "2025.")).all():
        raise RuntimeError("out-of-window/protected row present in I-B dataset")

    ic = load_ic_module(ic_engine)
    df = df.sort_values("server_epoch").reset_index(drop=True)
    df["year"] = df.server_time.str[:4].astype(int)
    dt = pd.to_datetime(df.server_time, format="%Y.%m.%d %H:%M:%S")
    df["month"] = dt.dt.month.astype(int)
    df["half"] = np.where(df["month"] <= 6, 1, 2)

    heartbeat(hb, 10, 100, "features")
    df = ic.build_features(df)
    horizons = sorted({int(x) for x in candidates["horizon_bars"].tolist()})
    heartbeat(hb, 25, 100, "labels")
    df = ic.add_labels(df, horizons)
    d25 = df[df.year == int(policy["confirmation_year"])].copy()

    for f, c in cuts.items():
        if f not in d25.columns:
            raise RuntimeError(f"frozen Phase I-C feature absent: {f}")
        d25[f + "__q"] = ic.assign_q(d25[f], c)

    mapping = {
        "mean_fwd_ret_atr": lambda h: f"fwd_ret_atr_h{h}",
        "move_ge_1atr": lambda h: f"move_ge_1atr_h{h}",
        "up_first_1atr": lambda h: f"up_first_1atr_h{h}",
    }
    rows: list[dict] = []
    total = max(1, len(candidates))

    for i, (_, c) in enumerate(candidates.iterrows(), start=1):
        feature = str(c["feature"])
        q = int(c["quintile"]) - 1
        h = int(c["horizon_bars"])
        outcome = str(c["outcome"])
        if outcome not in mapping:
            raise RuntimeError(f"unexpected outcome {outcome}")
        col = mapping[outcome](h)
        mask = d25[feature + "__q"].to_numpy() == q
        hour_block = c.get("hour_block")
        if pd.notna(hour_block):
            mask &= d25.hour_block.to_numpy() == int(float(hour_block))

        expected_sign = sign_of(float(c["confirmation_effect"]))
        if expected_sign == 0:
            continue
        min_effect = float(policy["minimum_absolute_effect"][outcome])
        values = d25[col].to_numpy(float)

        month_effects: list[float] = []
        month_details: dict[str, dict] = {}
        valid_months = 0
        same_sign_months = 0
        for m in range(1, 13):
            period = d25.month.to_numpy() == m
            res = signed_effect_test(ic, values[period], mask[period], outcome)
            if res is None or int(res["n_state"]) < int(policy["minimum_month_state_n"]):
                month_details[str(m)] = {"sufficient": False, "n_state": 0 if res is None else int(res["n_state"])}
                continue
            eff = float(res["effect"])
            valid_months += 1
            same = sign_of(eff) == expected_sign
            same_sign_months += int(same)
            month_effects.append(eff)
            month_details[str(m)] = {
                "sufficient": True,
                "n_state": int(res["n_state"]),
                "effect": eff,
                "same_sign": bool(same),
            }

        half_details: dict[str, dict] = {}
        halves_pass = True
        for half in (1, 2):
            period = d25.half.to_numpy() == half
            res = signed_effect_test(ic, values[period], mask[period], outcome)
            if res is None:
                half_details[str(half)] = {"sufficient": False}
                halves_pass = False
                continue
            eff = float(res["effect"])
            sufficient = int(res["n_state"]) >= int(policy["minimum_half_state_n"])
            same = sign_of(eff) == expected_sign
            effect_ok = abs(eff) >= min_effect
            half_details[str(half)] = {
                "sufficient": bool(sufficient),
                "n_state": int(res["n_state"]),
                "effect": eff,
                "same_sign": bool(same),
                "minimum_effect_pass": bool(effect_ok),
            }
            halves_pass &= sufficient and same and effect_ok

        min_valid = int(policy["minimum_valid_months"])
        needed_same = math.ceil(float(policy["minimum_same_sign_fraction"]) * valid_months) if valid_months else 999999
        median_effect = float(np.median(month_effects)) if month_effects else math.nan
        valid_pass = valid_months >= min_valid
        month_sign_pass = same_sign_months >= needed_same
        median_effect_pass = math.isfinite(median_effect) and sign_of(median_effect) == expected_sign and abs(median_effect) >= min_effect
        robust_pass = bool(valid_pass and month_sign_pass and median_effect_pass and halves_pass)

        row = {k: (None if pd.isna(v) else v) for k, v in c.to_dict().items()}
        row.update({
            "valid_months": valid_months,
            "same_sign_months": same_sign_months,
            "required_same_sign_months": needed_same if valid_months else None,
            "median_month_effect": None if not math.isfinite(median_effect) else median_effect,
            "minimum_effect": min_effect,
            "valid_months_pass": valid_pass,
            "month_sign_pass": month_sign_pass,
            "median_effect_pass": median_effect_pass,
            "halves_pass": bool(halves_pass),
            "robust_pass": robust_pass,
            "month_details": json.dumps(month_details, sort_keys=True),
            "half_details": json.dumps(half_details, sort_keys=True),
        })
        rows.append(row)
        if i % 50 == 0 or i == total:
            heartbeat(hb, 25 + int(65 * i / total), 100, "temporal_robustness")

    result = pd.DataFrame(rows)
    all_path = out / "phase_id_all_candidates.csv"
    robust_path = out / "phase_id_robust_survivors.csv"
    result.to_csv(all_path, index=False)
    robust = result[result.robust_pass == True].copy() if len(result) else result.copy()
    robust.to_csv(robust_path, index=False)

    by_outcome = {str(k): int(v) for k, v in robust.groupby("outcome").size().to_dict().items()} if len(robust) else {}
    by_horizon = {str(int(k)): int(v) for k, v in robust.groupby("horizon_bars").size().to_dict().items()} if len(robust) else {}
    distinct = int(robust[["state", "outcome", "horizon_bars"]].drop_duplicates().shape[0]) if len(robust) else 0
    summary = {
        "schema": 1,
        "phase": "I-D",
        "technical_status": "PASS",
        "scientific_status": "ROBUST_SURVIVORS_FOUND" if len(robust) else "NO_ROBUST_SURVIVORS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_phase_ic_survivors": int(len(candidates)),
        "candidates_retested": int(len(result)),
        "robust_survivor_count": int(len(robust)),
        "distinct_state_outcome_horizon_count": distinct,
        "robust_survivors_by_outcome": by_outcome,
        "robust_survivors_by_horizon": by_horizon,
        "policy": policy,
        "protected_2026_untouched": True,
        "propfirm_tradability_authorized": False,
        "next_rule": "A Phase I-D survivor remains a phenomenon candidate. The supervisor must deduplicate/translate and preregister any further confirmation before considering protected 2026; no PnL/sizing rescue is permitted.",
    }
    summary_path = out / "phase_id_summary.json"
    atomic_json(summary_path, summary)
    heartbeat(hb, 100, 100, "complete")

    publish(
        publisher,
        "PASS",
        f"Phase I-D technical PASS; scientific={summary['scientific_status']}; retested={len(result)}; robust_survivors={len(robust)}; 2026 untouched.",
        [summary_path, all_path, robust_path, Path(args.policy)],
        deploy,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
