#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "post_validation_pipeline_v1_00.py"
spec = importlib.util.spec_from_file_location("guardian_post_validation_pipeline", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class EligibilityPolicyTests(unittest.TestCase):
    def evaluate(self, obj, **kwargs):
        return mod.evaluate_scorer_eligibility(
            obj,
            accepted_verdicts=["CONFIRM"],
            expected_stage="CONFIRM_2026_H1",
            **kwargs,
        )

    def test_confirm_all_gates_true_is_eligible(self):
        r = self.evaluate({
            "verdict": "CONFIRM",
            "stage": "CONFIRM_2026_H1",
            "gates": {"a": True, "b": True},
        })
        self.assertTrue(r["challenge_lab_eligible"])
        self.assertEqual(r["failed_gates"], [])

    def test_unconfirmed_is_not_eligible(self):
        r = self.evaluate({
            "verdict": "UNCONFIRMED",
            "stage": "CONFIRM_2026_H1",
            "gates": {"a": True},
        })
        self.assertFalse(r["challenge_lab_eligible"])

    def test_false_gate_blocks_even_with_confirm_verdict(self):
        r = self.evaluate({
            "verdict": "CONFIRM",
            "stage": "CONFIRM_2026_H1",
            "gates": {"a": True, "b": False},
        })
        self.assertFalse(r["challenge_lab_eligible"])
        self.assertEqual(r["failed_gates"], ["b"])

    def test_wrong_stage_blocks(self):
        r = self.evaluate({
            "verdict": "CONFIRM",
            "stage": "DEV_2024_2025",
            "gates": {"a": True},
        })
        self.assertFalse(r["challenge_lab_eligible"])

    def test_empty_gates_fail_closed(self):
        r = self.evaluate({
            "verdict": "CONFIRM",
            "stage": "CONFIRM_2026_H1",
            "gates": {},
        })
        self.assertFalse(r["challenge_lab_eligible"])

    def test_legacy_missing_gates_requires_explicit_escape_hatch(self):
        r = self.evaluate({
            "verdict": "CONFIRM",
            "stage": "CONFIRM_2026_H1",
        }, allow_missing_gates=True)
        self.assertTrue(r["challenge_lab_eligible"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
