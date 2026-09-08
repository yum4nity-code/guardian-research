#!/usr/bin/env python3
"""Guardian post-validation pipeline v1.01.

Canonical bridge from a frozen scorer JSON to Challenge Probability Lab using a
pre-registered policy file. No verdict/stage/risk-grid decision is accepted from
ad-hoc CLI arguments after results are known.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

VERSION = "1.01"
PLACEHOLDER = "REPLACE_WITH_"


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


def validate_policy(policy: dict) -> dict:
    required = {
        "policy_id", "verdict_key", "accepted_verdicts", "stage_key", "expected_stage",
        "gates_key", "allow_missing_gates", "paths_per_risk", "seed", "risk_levels_pct",
        "expected_profile_sha256",
    }
    missing = sorted(required - set(policy))
    if missing:
        raise ValueError(f"policy missing keys: {missing}")
    if not isinstance(policy["policy_id"], str) or not policy["policy_id"].strip() or PLACEHOLDER in policy["policy_id"]:
        raise ValueError("policy_id must be frozen and non-placeholder")
    for key in ("verdict_key", "stage_key", "gates_key", "expected_stage"):
        if not isinstance(policy[key], str) or not policy[key].strip() or PLACEHOLDER in policy[key]:
            raise ValueError(f"{key} must be a frozen non-placeholder string")
    av = policy["accepted_verdicts"]
    if not isinstance(av, list) or not av or any(not isinstance(x, str) or not x.strip() or PLACEHOLDER in x for x in av):
        raise ValueError("accepted_verdicts must be a non-empty frozen string list")
    if not isinstance(policy["allow_missing_gates"], bool):
        raise ValueError("allow_missing_gates must be boolean")
    if not isinstance(policy["paths_per_risk"], int) or policy["paths_per_risk"] < 100:
        raise ValueError("paths_per_risk must be integer >= 100")
    if not isinstance(policy["seed"], int):
        raise ValueError("seed must be integer")
    rr = policy["risk_levels_pct"]
    if not isinstance(rr, list) or not rr:
        raise ValueError("risk_levels_pct must be a non-empty list")
    risks = [float(x) for x in rr]
    if any(not math.isfinite(x) or x <= 0 for x in risks):
        raise ValueError("risk levels must be positive finite percentages")
    sha = policy["expected_profile_sha256"]
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
        raise ValueError("expected_profile_sha256 must be a 64-char hex SHA256")
    return {**policy, "risk_levels_pct": risks, "expected_profile_sha256": sha.lower()}


def evaluate_scorer_eligibility(scorer: dict, policy: dict) -> dict:
    reasons: list[str] = []
    verdict_found, verdict = nested_get_optional(scorer, policy["verdict_key"])
    verdict_ok = verdict_found and isinstance(verdict, str) and verdict in set(policy["accepted_verdicts"])
    if not verdict_found:
        reasons.append(f"missing verdict key {policy['verdict_key']}")
    elif not isinstance(verdict, str):
        reasons.append("observed verdict is not a string")
    elif not verdict_ok:
        reasons.append(f"verdict {verdict!r} not in frozen accepted set")

    stage_found, stage = nested_get_optional(scorer, policy["stage_key"])
    stage_ok = stage_found and stage == policy["expected_stage"]
    if not stage_found:
        reasons.append(f"missing stage key {policy['stage_key']}")
    elif not stage_ok:
        reasons.append(f"stage {stage!r} != frozen expected {policy['expected_stage']!r}")

    gates_found, gates = nested_get_optional(scorer, policy["gates_key"])
    gates_ok = False
    failed_gates: list[str] = []
    gate_count = 0
    if gates_found and isinstance(gates, dict) and gates:
        gate_count = len(gates)
        failed_gates = sorted(str(k) for k, v in gates.items() if v is not True)
        gates_ok = not failed_gates
        if failed_gates:
            reasons.append("one or more frozen scorer gates are not true")
    elif policy["allow_missing_gates"]:
        gates_ok = True
        reasons.append("missing/empty gates explicitly permitted by frozen policy")
    else:
        reasons.append(f"missing, empty, or non-object gates at {policy['gates_key']}")

    return {
        "challenge_lab_eligible": bool(verdict_ok and stage_ok and gates_ok),
        "observed_verdict": verdict if verdict_found else None,
        "observed_stage": stage if stage_found else None,
        "gate_count": gate_count,
        "failed_gates": failed_gates,
        "reasons": reasons,
    }


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")


def main() -> int:
    here = Path(__file__).resolve().parent
    a = argparse.ArgumentParser(description="Guardian preregistered scorer -> Challenge Lab pipeline v1.01")
    a.add_argument("--scorer-json", required=True)
    a.add_argument("--policy", required=True, help="Frozen preregistered Challenge pipeline policy JSON")
    a.add_argument("--input", action="append", required=True, help="Frozen trade CSV; repeat as needed")
    a.add_argument("--profile", required=True, help="Frozen challenge profile JSON whose SHA256 is pinned in policy")
    a.add_argument("--output-dir", required=True)
    a.add_argument("--lab-stage")
    a.add_argument("--r-column")
    a.add_argument("--time-column")
    a.add_argument("--trading-days-only", action="store_true")
    a.add_argument("--allow-legacy-atomic-export", action="store_true")
    q = a.parse_args()

    scorer_path = Path(q.scorer_json)
    policy_path = Path(q.policy)
    profile_path = Path(q.profile)
    scorer = json.loads(scorer_path.read_text(encoding="utf-8"))
    policy = validate_policy(json.loads(policy_path.read_text(encoding="utf-8")))
    if not isinstance(scorer, dict):
        raise ValueError("scorer JSON root must be an object")

    profile_sha = sha256_file(profile_path)
    if profile_sha.lower() != policy["expected_profile_sha256"]:
        raise ValueError(
            f"challenge profile SHA256 mismatch: got {profile_sha}, expected {policy['expected_profile_sha256']}"
        )

    decision = evaluate_scorer_eligibility(scorer, policy)
    decision.update({
        "schema_version": 1,
        "pipeline_version": VERSION,
        "policy": {
            "path": str(policy_path),
            "sha256": sha256_file(policy_path),
            "policy_id": policy["policy_id"],
            "accepted_verdicts": policy["accepted_verdicts"],
            "expected_stage": policy["expected_stage"],
            "allow_missing_gates": policy["allow_missing_gates"],
            "paths_per_risk": policy["paths_per_risk"],
            "seed": policy["seed"],
            "risk_levels_pct": policy["risk_levels_pct"],
        },
        "source_scorer": {"path": str(scorer_path), "sha256": sha256_file(scorer_path)},
        "challenge_profile": {"path": str(profile_path), "sha256": profile_sha},
    })

    out_dir = Path(q.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    eligibility_path = out_dir / "challenge_lab_eligibility.json"
    write_json(eligibility_path, decision)

    gate = here / "post_validation_challenge_gate_v1_00.py"
    cmd = [
        sys.executable, str(gate),
        "--eligibility-json", str(eligibility_path),
        "--profile", str(profile_path),
        "--output-dir", str(out_dir),
        "--paths", str(policy["paths_per_risk"]),
        "--seed", str(policy["seed"]),
    ]
    for x in q.input:
        cmd += ["--input", x]
    for r in policy["risk_levels_pct"]:
        cmd += ["--risk", str(r)]
    if q.lab_stage:
        cmd += ["--stage", q.lab_stage]
    if q.r_column:
        cmd += ["--r-column", q.r_column]
    if q.time_column:
        cmd += ["--time-column", q.time_column]
    if q.trading_days_only:
        cmd.append("--trading-days-only")
    if q.allow_legacy_atomic_export:
        cmd.append("--allow-legacy-atomic-export")

    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
