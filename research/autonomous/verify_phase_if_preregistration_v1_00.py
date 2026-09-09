#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

EXPECTED = {
    "phase": "I-F",
    "name": "XAU_DIRECTIONAL_FINAL_OOS_V1",
    "status": "PREREGISTERED_SEALED",
    "owner_approval_required": True,
    "human_approved_2026_at_preregistration": False,
    "protected_2026_untouched_at_preregistration": True,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    args = ap.parse_args()
    p = Path(args.policy)
    o = json.loads(p.read_text(encoding="utf-8"))
    errors = []
    for k, v in EXPECTED.items():
        if o.get(k) != v:
            errors.append(f"{k}: expected {v!r}, got {o.get(k)!r}")
    c = o.get("candidate", {})
    checks = {
        "state": "bar_range_atr:Q5:H4",
        "feature": "bar_range_atr",
        "quintile": 5,
        "frozen_q5_lower_cutpoint": 1.2604033158741452,
        "hour_block": 4,
        "horizon_bars": 12,
        "outcome": "mean_fwd_ret_atr",
        "expected_sign": -1,
        "minimum_absolute_effect_atr": 0.06,
    }
    for k, v in checks.items():
        if c.get(k) != v:
            errors.append(f"candidate.{k}: expected {v!r}, got {c.get(k)!r}")
    w = o.get("final_oos_window", {})
    if w.get("start_server_time_inclusive") != "2026.01.01 00:00:00":
        errors.append("final_oos_window start mismatch")
    if w.get("end_server_time_exclusive") != "2026.09.01 00:00:00":
        errors.append("final_oos_window end mismatch")
    if o.get("data_provenance", {}).get("dataset_integrity_must_pass_before_candidate_evaluation") is not True:
        errors.append("dataset integrity prerequisite missing")
    if errors:
        print(json.dumps({"status":"FAIL","errors":errors}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({
        "status":"PASS",
        "phase":"I-F-PREREGISTRATION",
        "policy":str(p),
        "protected_2026_untouched":True,
        "owner_approval_required":True
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
