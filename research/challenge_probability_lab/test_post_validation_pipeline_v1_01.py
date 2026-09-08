#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "post_validation_pipeline_v1_01.py"
spec = importlib.util.spec_from_file_location("guardian_post_validation_pipeline_v101", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def base_policy():
    return {
        "policy_id": "D999_CONFIRM_CHALLENGE_V1",
        "verdict_key": "verdict",
        "accepted_verdicts": ["CONFIRM"],
        "stage_key": "stage",
        "expected_stage": "CONFIRM_2026_H1",
        "gates_key": "gates",
        "allow_missing_gates": False,
        "paths_per_risk": 20000,
        "seed": 20260907,
        "risk_levels_pct": [0.10, 0.15, 0.20, 0.25, 0.33, 0.50],
        "expected_profile_sha256": "0" * 64,
    }


class PreregisteredPolicyTests(unittest.TestCase):
    def test_confirm_all_gates_true_is_eligible(self):
        p = mod.validate_policy(base_policy())
        r = mod.evaluate_scorer_eligibility({
            "verdict": "CONFIRM",
            "stage": "CONFIRM_2026_H1",
            "gates": {"a": True, "b": True},
        }, p)
        self.assertTrue(r["challenge_lab_eligible"])

    def test_unconfirmed_is_blocked(self):
        p = mod.validate_policy(base_policy())
        r = mod.evaluate_scorer_eligibility({
            "verdict": "UNCONFIRMED",
            "stage": "CONFIRM_2026_H1",
            "gates": {"a": True},
        }, p)
        self.assertFalse(r["challenge_lab_eligible"])

    def test_wrong_stage_is_blocked(self):
        p = mod.validate_policy(base_policy())
        r = mod.evaluate_scorer_eligibility({
            "verdict": "CONFIRM",
            "stage": "DEV_2024_2025",
            "gates": {"a": True},
        }, p)
        self.assertFalse(r["challenge_lab_eligible"])

    def test_false_gate_is_blocked(self):
        p = mod.validate_policy(base_policy())
        r = mod.evaluate_scorer_eligibility({
            "verdict": "CONFIRM",
            "stage": "CONFIRM_2026_H1",
            "gates": {"a": True, "b": False},
        }, p)
        self.assertFalse(r["challenge_lab_eligible"])
        self.assertEqual(r["failed_gates"], ["b"])

    def test_placeholder_stage_is_rejected(self):
        p = base_policy()
        p["expected_stage"] = "REPLACE_WITH_STAGE"
        with self.assertRaises(ValueError):
            mod.validate_policy(p)

    def test_empty_risk_grid_is_rejected(self):
        p = base_policy()
        p["risk_levels_pct"] = []
        with self.assertRaises(ValueError):
            mod.validate_policy(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
