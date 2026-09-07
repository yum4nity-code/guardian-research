#!/usr/bin/env python3
from __future__ import annotations
import unittest
import management_benchmark as m


def row(**overrides):
    base = {
        "symbol": "BTCUSD",
        "gross_r": "0.25",
        "commission_r": "0.05",
        "net_r": "0.20",
        "net_r_commission_x1_5": "0.175",
        "exit_reason": "EOD",
        "path_ambiguous": "0",
        "mae_r": "0.40",
        "reached_0_5r": "1",
        "mae_before_0_5r": "0.20",
        "reached_1r": "1",
        "mae_before_1r": "0.30",
        "reached_2r": "0",
        "mae_before_2r": "",
        "reached_3r": "0",
        "mae_before_3r": "",
        "min_r_after_first_1r_before_exit": "-0.10",
        "min_r_after_first_2r_before_exit": "",
    }
    base.update({k: str(v) for k, v in overrides.items()})
    return base


def rule(name):
    return next(x for x in m.RULES if x["name"] == name)


class ManagementBenchmarkTests(unittest.TestCase):
    def test_baseline_exact(self):
        gross, reason = m.apply_rule(row(), rule("BASELINE_ORIGINAL"))
        self.assertEqual(0.25, gross)
        self.assertEqual("ORIGINAL_EXIT", reason)

    def test_full_tp_uses_saved_milestone(self):
        gross, reason = m.apply_rule(row(), rule("SL1_TP1"))
        self.assertEqual(1.0, gross)
        self.assertEqual("TP_THRESHOLD_PROXY", reason)

    def test_narrow_stop_precedes_tp_from_mae_before(self):
        gross, reason = m.apply_rule(row(mae_before_1r="0.70"), rule("SL0_5_TP1"))
        self.assertEqual(-0.5, gross)
        self.assertEqual("SL_BEFORE_TP_THRESHOLD_PROXY", reason)

    def test_be_after_1r_recross(self):
        gross, reason = m.apply_rule(row(min_r_after_first_1r_before_exit="-0.01"), rule("BE_AFTER_1R"))
        self.assertEqual(0.0, gross)
        self.assertEqual("BE_THRESHOLD_PROXY", reason)

    def test_be_after_1r_without_recross_keeps_original(self):
        gross, reason = m.apply_rule(row(min_r_after_first_1r_before_exit="0.20"), rule("BE_AFTER_1R"))
        self.assertEqual(0.25, gross)
        self.assertEqual("ORIGINAL_EXIT_NO_BE_RECROSS", reason)

    def test_partial_at_1r(self):
        gross, _ = m.apply_rule(row(), rule("P50_AT_1R_REST_ORIGINAL"))
        self.assertAlmostEqual(0.625, gross)

    def test_partial_plus_be(self):
        gross, _ = m.apply_rule(row(min_r_after_first_1r_before_exit="-0.10"), rule("P50_AT_1R_BE_REST"))
        self.assertAlmostEqual(0.5, gross)

    def test_ambiguous_alternate_is_excluded(self):
        gross, reason = m.apply_rule(row(path_ambiguous="1"), rule("SL1_TP1"))
        self.assertIsNone(gross)
        self.assertEqual("EXCLUDED_PATH_AMBIGUOUS", reason)

    def test_rank_prefers_breadth_then_worst_family(self):
        matrix = [
            {"rule": "SL1_TP1", "dataset": "A", "mean_net_delta_vs_baseline": 0.10},
            {"rule": "SL1_TP1", "dataset": "B", "mean_net_delta_vs_baseline": 0.05},
            {"rule": "SL1_TP1", "dataset": "C", "mean_net_delta_vs_baseline": -0.01},
            {"rule": "SL1_TP1", "dataset": "D", "mean_net_delta_vs_baseline": 0.02},
            {"rule": "SL1_TP2", "dataset": "A", "mean_net_delta_vs_baseline": 0.50},
            {"rule": "SL1_TP2", "dataset": "B", "mean_net_delta_vs_baseline": 0.50},
            {"rule": "SL1_TP2", "dataset": "C", "mean_net_delta_vs_baseline": -0.50},
            {"rule": "SL1_TP2", "dataset": "D", "mean_net_delta_vs_baseline": -0.50},
        ]
        # cross_family expects all frozen rules but missing rules are safely ranked later.
        deltas = {x["name"]: [] for x in m.RULES}
        deltas["SL1_TP1"] = [0.10, 0.05, -0.01, 0.02]
        deltas["SL1_TP2"] = [0.50, 0.50, -0.50, -0.50]
        ranked = m.cross_family(matrix, deltas)
        names = [x["rule"] for x in ranked]
        self.assertLess(names.index("SL1_TP1"), names.index("SL1_TP2"))


if __name__ == "__main__":
    unittest.main()
