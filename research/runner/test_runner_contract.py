#!/usr/bin/env python3
"""Pure-Python regression checks for tester/scorer contracts."""

from __future__ import annotations

import unittest

import experiment
import score
import tester


class RunnerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.manifest = experiment.load_manifest("D037")

    def test_d037_output_names_are_deterministic(self) -> None:
        stats, trades = tester.expected_output_names(self.manifest, "development", "EURUSD")
        self.assertEqual("D037_V101_DEV_2024_2025_EURUSD_STATS.csv", stats)
        self.assertEqual("D037_V101_DEV_2024_2025_EURUSD_TRADES.csv", trades)

    def test_d037_reference_ini_is_non_optimizing_and_local(self) -> None:
        stage = self.manifest["stages"]["development"]
        ini = tester.render_tester_ini(self.manifest, "development", stage, "USDJPY", 0)
        self.assertIn("Expert=GuardianResearch\\D037_Williams_M15_v1_01", ini)
        self.assertIn("Symbol=USDJPY", ini)
        self.assertIn("Period=M15", ini)
        self.assertIn("Model=0", ini)
        self.assertIn("Optimization=0", ini)
        self.assertIn("FromDate=2024.01.02", ini)
        self.assertIn("ToDate=2025.12.31", ini)
        self.assertIn("UseLocal=1", ini)
        self.assertIn("UseRemote=0", ini)
        self.assertIn("UseCloud=0", ini)
        self.assertIn("ShutdownTerminal=1", ini)

    def test_reference_and_fast_models_are_explicit(self) -> None:
        contract = self.manifest["runner_contract"]
        self.assertEqual(0, contract["tester_model_reference"])
        self.assertEqual(1, contract["tester_model_fast_candidate"])

    def test_profit_factor_zero_loss_stays_json_safe(self) -> None:
        pf, infinite = score.profit_factor_parts([1.0, 0.5, 0.0])
        self.assertIsNone(pf)
        self.assertTrue(infinite)

    def test_entry_year_parses_mql5_time_string(self) -> None:
        self.assertEqual(2025, score.entry_year("2025.07.31 15:45"))


if __name__ == "__main__":
    unittest.main()
