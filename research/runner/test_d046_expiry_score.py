#!/usr/bin/env python3
from __future__ import annotations

import unittest

import d046_expiry_score as score


def leg(day: str, name: str, net: float, stress: float | None = None, eligible: bool = True) -> dict[str, str]:
    if stress is None:
        stress = net - 4.0
    return {
        "utc_day_key": day,
        "leg": name,
        "side": "SHORT" if name == "PRE_SHORT" else "LONG",
        "eligible": "1" if eligible else "0",
        "entry_delay_seconds": "0",
        "exit_delay_seconds": "1",
        "commission_bps": "8",
        "gross_bps": str(net + 8.0),
        "net_bps": str(net),
        "net_bps_commission_x1_5": str(stress),
    }


def gates(n: int = 2) -> dict:
    return {
        "paired_days_min": n,
        "combined_day_pf_min": 1.10,
        "bootstrap_resamples": 200,
        "bootstrap_seed": 460800,
        "count_failure_verdict": "INCONCLUSIVE_COUNT",
        "failure_verdict": "REJECT_UNCONDITIONAL_SCREEN",
        "pass_verdict": "UNCONDITIONAL_EXPIRY_SCREEN_PASS",
    }


class D046ExpiryScoreTests(unittest.TestCase):
    def test_pairs_only_complete_days(self):
        rows = [
            leg("20240102", "PRE_SHORT", 5), leg("20240102", "POST_LONG", 5),
            leg("20240103", "PRE_SHORT", 9),
            leg("20240104", "POST_LONG", 9),
        ]
        paired = score.pair_rows(rows)
        self.assertEqual(1, len(paired["paired_days"]))
        self.assertEqual(2, paired["unpaired_eligible_days"])

    def test_rejects_eligible_boundary_later_than_300s(self):
        row = leg("20240102", "PRE_SHORT", 5)
        row["entry_delay_seconds"] = "301"
        with self.assertRaises(score.D046ScoreError):
            score.pair_rows([row])

    def test_rejects_wrong_commission(self):
        row = leg("20240102", "PRE_SHORT", 5)
        row["commission_bps"] = "7.9"
        with self.assertRaises(score.D046ScoreError):
            score.pair_rows([row])

    def test_positive_two_year_sample_passes(self):
        rows = []
        for day in ("20240102", "20240103", "20250102", "20250103"):
            rows += [leg(day, "PRE_SHORT", 6), leg(day, "POST_LONG", 7)]
        g = gates(4)
        result = score.evaluate(rows, g, "development")
        self.assertEqual("UNCONDITIONAL_EXPIRY_SCREEN_PASS", result["verdict"])
        self.assertTrue(result["all_gates_pass"])

    def test_negative_post_leg_fails_even_if_combined_positive(self):
        rows = []
        for day in ("20240102", "20240103", "20250102", "20250103"):
            rows += [leg(day, "PRE_SHORT", 20), leg(day, "POST_LONG", -2, stress=-6)]
        result = score.evaluate(rows, gates(4), "development")
        self.assertEqual("REJECT_UNCONDITIONAL_SCREEN", result["verdict"])
        self.assertFalse(result["gates"]["post_long_mean_net_bps_strictly_positive"])

    def test_count_failure_is_inconclusive(self):
        rows = [leg("20240102", "PRE_SHORT", 6), leg("20240102", "POST_LONG", 7)]
        result = score.evaluate(rows, gates(2), "development")
        self.assertEqual("INCONCLUSIVE_COUNT", result["verdict"])


if __name__ == "__main__":
    unittest.main()
