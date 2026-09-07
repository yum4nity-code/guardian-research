#!/usr/bin/env python3
"""Guardian post-validation Challenge Probability gate v1.00.

This wrapper is the standard downstream bridge between a strategy confirmation/OOS
verdict and Challenge Probability Lab. It deliberately refuses to infer alpha
eligibility from arbitrary status strings: the upstream scorer must persist an
explicit boolean `challenge_lab_eligible` (or a caller-selected key).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

from challenge_probability_lab_v1_00 import (
    DEFAULT_RISKS,
    LabConfig,
    build_day_blocks,
    load_trades,
    render_markdown,
    run_lab,
    write_csv,
)

VERSION = "1.00"
CANONICAL_DAY_COLUMN = "challenge_day"
CANONICAL_ADVERSE_COLUMN = "adverse_r"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def nested_get(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(f"missing JSON key {dotted!r} at {part!r}")
        cur = cur[part]
    return cur


def sniff_header(path: Path) -> tuple[list[str], str]:
    raw = path.read_text(encoding="utf-8-sig")
    first = raw.splitlines()[0] if raw.splitlines() else ""
    delim = max((",", ";", "\t"), key=first.count)
    reader = csv.reader([first], delimiter=delim)
    fields = next(reader, [])
    return fields, delim


def canonical_export_audit(paths: Sequence[str]) -> dict:
    rows = []
    all_day = True
    all_adverse = True
    for p0 in paths:
        p = Path(p0)
        fields, delim = sniff_header(p)
        has_day = CANONICAL_DAY_COLUMN in fields
        has_adverse = CANONICAL_ADVERSE_COLUMN in fields
        all_day = all_day and has_day
        all_adverse = all_adverse and has_adverse
        rows.append({
            "path": str(p),
            "sha256": sha256_file(p),
            "delimiter": delim,
            "has_challenge_day": has_day,
            "has_adverse_r": has_adverse,
        })
    fidelity = (
        "ATOMIC_PLUS_INDIVIDUAL_ADVERSE_R"
        if all_day and all_adverse
        else "ATOMIC_CLOSED_EQUITY"
    )
    return {
        "files": rows,
        "canonical_challenge_day_all_inputs": all_day,
        "canonical_adverse_r_all_inputs": all_adverse,
        "dd_fidelity": fidelity,
    }


def load_profile(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("profile root must be an object")
    return obj


def choose(cli, profile: dict, key: str, default):
    return cli if cli is not None else profile.get(key, default)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")


def main() -> int:
    here = Path(__file__).resolve().parent
    a = argparse.ArgumentParser(description="Guardian post-validation Challenge Probability gate v1.00")
    a.add_argument("--input", action="append", required=True, help="Frozen validated trade CSV; repeat for multiple files")
    a.add_argument("--eligibility-json", required=True, help="Upstream OOS/confirmation decision JSON")
    a.add_argument("--eligibility-key", default="challenge_lab_eligible", help="Boolean JSON key, dotted path allowed")
    a.add_argument("--profile", default=str(here / "guardian_reference_profile_v1_00.json"))
    a.add_argument("--output-dir", required=True)
    a.add_argument("--stage")
    a.add_argument("--paths", type=int, default=20000)
    a.add_argument("--seed", type=int, default=20260907)
    a.add_argument("--risk", action="append", type=float, dest="risks")
    a.add_argument("--r-column")
    a.add_argument("--time-column")
    a.add_argument("--initial-balance", type=float)
    a.add_argument("--profit-target-pct", type=float)
    a.add_argument("--daily-loss-pct", type=float)
    a.add_argument("--max-loss-pct", type=float)
    a.add_argument("--max-days", type=int)
    a.add_argument("--block-days", type=int)
    a.add_argument("--risk-basis", choices=("initial", "current"))
    a.add_argument("--max-loss-anchor", choices=("initial", "trailing_eod"))
    a.add_argument("--trading-days-only", action="store_true")
    a.add_argument(
        "--allow-legacy-atomic-export",
        action="store_true",
        help="Allow validated legacy CSVs without canonical challenge_day/adverse_r. Output is marked lower-fidelity.",
    )
    q = a.parse_args()

    out_dir = Path(q.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "challenge_gate_manifest.json"

    eligibility_path = Path(q.eligibility_json)
    eligibility_obj = json.loads(eligibility_path.read_text(encoding="utf-8"))
    eligible = nested_get(eligibility_obj, q.eligibility_key)
    if not isinstance(eligible, bool):
        raise TypeError(f"{q.eligibility_key!r} must be a JSON boolean, got {type(eligible).__name__}")

    audit = canonical_export_audit(q.input)
    base_manifest = {
        "schema_version": 1,
        "gate": "GUARDIAN_POST_VALIDATION_CHALLENGE_PROBABILITY",
        "gate_version": VERSION,
        "eligibility_source": {
            "path": str(eligibility_path),
            "sha256": sha256_file(eligibility_path),
            "key": q.eligibility_key,
            "value": eligible,
        },
        "input_contract": audit,
    }

    if not eligible:
        write_json(manifest_path, {
            **base_manifest,
            "status": "SKIPPED_NOT_ALPHA_VALIDATED",
            "reason": "upstream scorer did not mark the frozen strategy/portfolio challenge_lab_eligible",
            "lab_ran": False,
        })
        print("Challenge Lab skipped: upstream validation did not mark this result eligible.")
        print(f"Manifest: {manifest_path}")
        return 0

    if not audit["canonical_challenge_day_all_inputs"] and not q.allow_legacy_atomic_export:
        raise ValueError(
            "validated input is missing canonical 'challenge_day'; future post-validation runs must export it. "
            "Use --allow-legacy-atomic-export only for explicitly accepted legacy evidence."
        )

    profile_path = Path(q.profile)
    profile = load_profile(profile_path)
    cfg = LabConfig(
        float(choose(q.initial_balance, profile, "initial_balance", 100000)),
        float(choose(q.profit_target_pct, profile, "profit_target_pct", 10)),
        float(choose(q.daily_loss_pct, profile, "daily_loss_pct", 5)),
        float(choose(q.max_loss_pct, profile, "max_loss_pct", 10)),
        int(choose(q.max_days, profile, "max_days", 730)),
        int(choose(q.block_days, profile, "block_days", 5)),
        str(choose(q.risk_basis, profile, "risk_basis", "initial")),
        str(choose(q.max_loss_anchor, profile, "max_loss_anchor", "initial")),
        not q.trading_days_only,
    )
    risks = q.risks or profile.get("risk_levels_pct") or list(DEFAULT_RISKS)
    if q.paths < 100:
        raise ValueError("paths must be >= 100")
    if any(not math.isfinite(float(x)) or float(x) <= 0 for x in risks):
        raise ValueError("risk levels must be positive finite percentages")

    day_column = CANONICAL_DAY_COLUMN if audit["canonical_challenge_day_all_inputs"] else None
    adverse_column = CANONICAL_ADVERSE_COLUMN if audit["canonical_adverse_r_all_inputs"] else None
    trades, meta = load_trades(
        q.input,
        r_column=q.r_column,
        time_column=q.time_column,
        day_column=day_column,
        adverse_r_column=adverse_column,
        stage=q.stage,
    )
    days = build_day_blocks(trades, dense_calendar=cfg.dense_calendar)
    rep = run_lab(
        days,
        cfg,
        risks=risks,
        paths=q.paths,
        seed=q.seed,
        use_adverse_r=bool(adverse_column),
    )
    rep["input"] = {
        **meta,
        "stage_filter": q.stage,
        "day_mode": "dense_calendar" if cfg.dense_calendar else "observed_trade_days_only",
        "challenge_export_contract": audit,
    }
    rep["post_validation_gate"] = {
        "eligibility_json": str(eligibility_path),
        "eligibility_sha256": sha256_file(eligibility_path),
        "eligibility_key": q.eligibility_key,
        "canonical_export_required": not q.allow_legacy_atomic_export,
        "dd_fidelity": audit["dd_fidelity"],
    }
    rep["warnings"] = []
    if not adverse_column:
        rep["warnings"].append("No canonical adverse_r supplied: DD probabilities can understate floating-equity breaches.")
    if not day_column:
        rep["warnings"].append("No canonical challenge_day supplied: legacy entry-date grouping was used.")
    if meta["cross_day_trade_count"]:
        rep["warnings"].append(
            f"{meta['cross_day_trade_count']} trades cross calendar days; trade-atomic assignment cannot reconstruct exact portfolio mark-to-market DD."
        )

    prefix = out_dir / "challenge_probability"
    json_path = Path(str(prefix) + ".json")
    csv_path = Path(str(prefix) + ".csv")
    md_path = Path(str(prefix) + ".md")
    write_json(json_path, rep)
    write_csv(rep, csv_path)
    md_path.write_text(render_markdown(rep), encoding="utf-8")

    write_json(manifest_path, {
        **base_manifest,
        "status": "CHALLENGE_LAB_COMPLETE",
        "lab_ran": True,
        "profile": {"path": str(profile_path), "sha256": sha256_file(profile_path)},
        "paths_per_risk": q.paths,
        "seed": q.seed,
        "risk_levels_pct": [float(x) for x in risks],
        "dd_fidelity": audit["dd_fidelity"],
        "optimal_risk_for_pass_pct": rep["optimal_risk_for_pass_pct"],
        "optimal_risk_pass_probability": rep["optimal_risk_pass_probability"],
        "outputs": {
            "json": str(json_path),
            "csv": str(csv_path),
            "markdown": str(md_path),
        },
    })

    print(render_markdown(rep), end="")
    print(f"Gate manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
