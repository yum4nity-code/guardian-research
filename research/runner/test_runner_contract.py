#!/usr/bin/env python3
"""Pure-Python regression checks for tester/scorer contracts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import experiment
import runner
import score
import tester


class RunnerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.manifest = experiment.load_manifest("D037")

    def test_d037_output_names_are_deterministic(self) -> None:
        stats, trades = tester.expected_output_names(self.manifest, "development", "EURUSD")
        self.assertEqual("D037_V102_DEV_2024_2025_EURUSD_STATS.csv", stats)
        self.assertEqual("D037_V102_DEV_2024_2025_EURUSD_TRADES.csv", trades)

    def test_d037_reference_ini_is_non_optimizing_and_local(self) -> None:
        stage = self.manifest["stages"]["development"]
        ini = tester.render_tester_ini(self.manifest, "development", stage, "USDJPY", 0)
        self.assertIn("Expert=GuardianResearch\\D037_Williams_M15_v1_02", ini)
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

    def test_d037_v102_zero_range_clarification_is_generic(self) -> None:
        self.assertEqual("1.02", self.manifest["source"]["version"])
        source = runner.ROOT / self.manifest["source"]["canonical_path"]
        text = source.read_text(encoding="utf-8")
        self.assertIn("SKIP_NO_REFERENCE_RANGE", text)
        self.assertIn("g_no_reference_range_days", text)
        self.assertIn("if(prev_range==0.0)", text)
        self.assertNotIn('if(StringFind(_Symbol,"XAUUSD")>=0 && prev_range==0.0)', text)

    def test_reference_and_fast_models_are_explicit(self) -> None:
        contract = self.manifest["runner_contract"]
        self.assertEqual(0, contract["tester_model_reference"])
        self.assertEqual(1, contract["tester_model_fast_candidate"])

    def test_source_identity_ignores_only_line_ending_checkout_difference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lf = root / "lf.mq5"
            crlf = root / "crlf.mq5"
            lf.write_bytes(b"#property strict\nint x=1;\n")
            crlf.write_bytes(b"#property strict\r\nint x=1;\r\n")
            self.assertNotEqual(runner.sha256_file(lf), runner.sha256_file(crlf))
            self.assertEqual(runner.sha256_text_lf(lf), runner.sha256_text_lf(crlf))

    def test_source_identity_still_detects_real_code_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.mq5"
            b = root / "b.mq5"
            a.write_bytes(b"#property strict\nint x=1;\n")
            b.write_bytes(b"#property strict\r\nint x=2;\r\n")
            self.assertNotEqual(runner.sha256_text_lf(a), runner.sha256_text_lf(b))

    def test_mt5_utf16_csv_with_bom_is_decoded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mt5.csv"
            path.write_bytes("status;trades_opened\r\nFINAL;12\r\n".encode("utf-16"))
            text, encoding = tester.decode_csv_text(path)
            rows = tester.read_semicolon_csv(path)
            self.assertEqual("utf-16", encoding)
            self.assertIn("FINAL;12", text)
            self.assertEqual("FINAL", rows[0]["status"])
            self.assertEqual("12", rows[0]["trades_opened"])

    def test_utf8_sig_csv_still_decodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "utf8.csv"
            path.write_bytes(b"\xef\xbb\xbfstatus;value\nREADY;1\n")
            _, encoding = tester.decode_csv_text(path)
            rows = tester.read_semicolon_csv(path)
            self.assertEqual("utf-8-sig", encoding)
            self.assertEqual("READY", rows[0]["status"])

    def test_profit_factor_zero_loss_stays_json_safe(self) -> None:
        pf, infinite = score.profit_factor_parts([1.0, 0.5, 0.0])
        self.assertIsNone(pf)
        self.assertTrue(infinite)

    def test_entry_year_parses_mql5_time_string(self) -> None:
        self.assertEqual(2025, score.entry_year("2025.07.31 15:45"))


if __name__ == "__main__":
    unittest.main()
