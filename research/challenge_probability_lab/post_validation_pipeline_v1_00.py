#!/usr/bin/env python3
"""Guardian post-validation pipeline v1.00.

Bridges a frozen strategy scorer JSON to Challenge Probability Lab without
modifying the frozen scorer. Eligibility is exact-match and fail-closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

VERSION = "1.00"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def nested_get_optional(obj: Any, dotted: str) -> tuple[bool, Any]:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def evaluate_scorer_eligibility(
    scorer: dict,
    *,
    accepted_verdicts: Sequence[str],
    verdict_key: str = "verdict",
    expected_stage: str | None = None,
    stage_key: str = "stage",
    gates_key: str = "gates",
    allow_missing_gates: bool = False,
) -> dict:
    if not accepted_verdicts:
        raise ValueError("at least one accepted verdict must be frozen explicitly")

    reasons: list[str] = []
    verdict_found, verdict = nested_get_optional(scorer, verdict_key)
    verdict_ok = verdict_found and isinstance(verdict, str) and verdict in set(accepted_verdicts)
    if not verdict_found:
        reasons.append(f"missing verdict key {verdict_key}")
    elif not isinstance(verdict, str):
        reasons.append(f"verdict at {verdict_key} is not a string")
    elif not verdict_ok:
        reasons.append(f"verdict {verdict!r} not in frozen accepted set")

    stage_found, stage = nested_get_optional(scorer, stage_key)
    stage_ok = True
    if expected_stage is not None:
        stage_ok = stage_found and stage == expected_stage
        if not stage_found:
            reasons.append(f"missing stage key {stage_key}")
        elif stage != expected_stage:
            reasons.append(f"stage {stage!r} != expected {expected_stage!r}")

    gates_found, gates = nested_get_optional(scorer, gates_key)
    gates_ok = False
    gate_count = 0
    failed_gates: list[str] = []
    if gates_found and isinstance(gates, dict) and gates:
        gate_count = len(gates)
        failed_gates = sorted(str(k) for k, v in gates.items() if v is not True)
        gates_ok = not failed_gates
        if failed_gates:
            reasons.append("one or more frozen scorer gates are not true")
    elif allow_missing_gates:
        gates_ok = True
        reasons.append("missing/empty gates explicitly allowed by caller")
    else:
        reasons.append(f"missing, empty, or non-object gates at {gates_key}")

    eligible = bool(verdict_ok and stage_ok and gates_ok)
    return {
        "challenge_lab_eligible": eligible,
        "policy_version": VERSION,
        "observed_verdict": verdict if verdict_found else None,
        "accepted_verdicts": list(accepted_verdicts),
        "verdict_key": verdict_key,
        "observed_stage": stage if stage_found else None,
        "expected_stage": expected_stage,
        "stage_key": stage_key,
        "gates_key": gates_key,
        "gates_present_nonempty": bool(gates_found and isinstance(gates, dict) and gates),
        "gate_count": gate_count,
        "failed_gates": failed_gates,
        "allow_missing_gates": allow_missing_gates,
        "reasons": reasons,
    }


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")


def main() -> int:
    here = Path(__file__).resolve().parent
    a = argparse.ArgumentParser(description="Guardian frozen-scorer -> Challenge Lab pipeline v1.00")
    a.add_argument("--scorer-json", required=True)
    a.add_argument("--accepted-verdict", action="append", required=True,
                   help="Exact verdict allowed to advance; repeat if preregistration explicitly permits several")
    a.add_argument("--verdict-key", default="verdict")
    a.add_argument("--expected-stage")
    a.add_argument("--stage-key", default="stage")
    a.add_argument("--gates-key", default="gates")
    a.add_argument("--allow-missing-gates", action="store_true",
                   help="Explicit escape hatch only for legacy scorers with no gate object")
    a.add_argument("--input", action="append", required=True, help="Frozen trade CSV; repeat as needed")
    a.add_argument("--profile", default=str(here / "guardian_reference_profile_v1_00.json"))
    a.add_argument("--output-dir", required=True)
    a.add_argument("--lab-stage")
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
    a.add_argument("--allow-legacy-atomic-export", action="store_true")
    q = a.parse_args()

    scorer_path = Path(q.scorer_json)
    scorer = json.loads(scorer_path.read_text(encoding="utf-8"))
    if not isinstance(scorer, dict):
        raise ValueError("scorer JSON root must be an object")

    decision = evaluate_scorer_eligibility(
        scorer,
        accepted_verdicts=q.accepted_verdict,
        verdict_key=q.verdict_key,
        expected_stage=q.expected_stage,
        stage_key=q.stage_key,
        gates_key=q.gates_key,
        allow_missing_gates=q.allow_missing_gates,
    )
    decision["schema_version"] = 1
    decision["source_scorer"] = {
        "path": str(scorer_path),
        "sha256": sha256_file(scorer_path),
    }

    out_dir = Path(q.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    eligibility_path = out_dir / "challenge_lab_eligibility.json"
    write_json(eligibility_path, decision)

    gate = here / "post_validation_challenge_gate_v1_00.py"
    cmd = [
        sys.executable, str(gate),
        "--eligibility-json", str(eligibility_path),
        "--profile", q.profile,
        "--output-dir", str(out_dir),
        "--paths", str(q.paths),
        "--seed", str(q.seed),
    ]
    for x in q.input:
        cmd += ["--input", x]
    if q.lab_stage:
        cmd += ["--stage", q.lab_stage]
    for r in q.risks or []:
        cmd += ["--risk", str(r)]
    for flag, value in (
        ("--r-column", q.r_column),
        ("--time-column", q.time_column),
        ("--initial-balance", q.initial_balance),
        ("--profit-target-pct", q.profit_target_pct),
        ("--daily-loss-pct", q.daily_loss_pct),
        ("--max-loss-pct", q.max_loss_pct),
        ("--max-days", q.max_days),
        ("--block-days", q.block_days),
        ("--risk-basis", q.risk_basis),
        ("--max-loss-anchor", q.max_loss_anchor),
    ):
        if value is not None:
            cmd += [flag, str(value)]
    if q.trading_days_only:
        cmd.append("--trading-days-only")
    if q.allow_legacy_atomic_export:
        cmd.append("--allow-legacy-atomic-export")

    completed = subprocess.run(cmd)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
