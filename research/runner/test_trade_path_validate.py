#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import trade_path_validate


class TradePathValidateTests(unittest.TestCase):
    def test_valid_single_trade_path_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stats = root / "stats.csv"
            trades = root / "trades.csv"

            stats.write_text(
                "status;trades_opened;trades_closed;csv_trade_rows;path_rows;path_calc_failures\n"
                "INIT;0;0;0;0;0\n"
                "READY;0;0;0;0;0\n"
                "FINAL;1;1;1;1;0\n",
                encoding="utf-8",
            )

            row = {field: "" for field in trade_path_validate.REQUIRED_PATH_COLUMNS}
            row.update({
                "trade_id": "USDJPY_20231101_LONG",
                "mfe_r": "1.25",
                "mae_r": "0.40",
                "mfe_time": "2023.11.01 12:00:00",
                "mae_time": "2023.11.01 09:00:00",
                "time_to_mfe_minutes": "180",
                "time_to_mae_minutes": "15",
                "max_retracement_from_mfe_r": "0.50",
                "reached_0_5r": "1",
                "first_touch_0_5r_time": "2023.11.01 10:00:00",
                "time_to_0_5r_minutes": "60",
                "mae_before_0_5r": "0.40",
                "reached_1r": "1",
                "first_touch_1r_time": "2023.11.01 11:00:00",
                "time_to_1r_minutes": "120",
                "mae_before_1r": "0.40",
                "reached_2r": "0",
                "reached_3r": "0",
                "reached_5r": "0",
                "min_r_after_first_1r_before_exit": "0.75",
                "max_r_after_first_1r_before_exit": "1.25",
                "path_ambiguous": "0",
                "path_ambiguity_reason": "",
            })
            header = trade_path_validate.REQUIRED_PATH_COLUMNS
            trades.write_text(
                ";".join(header) + "\n" + ";".join(row[field] for field in header) + "\n",
                encoding="utf-8",
            )

            result = trade_path_validate.validate_paths(stats, trades)
            self.assertEqual("TRADE_PATH_PASS", result["status"])
            self.assertEqual(1, result["trades"])
            self.assertEqual(1, result["path_rows"])
            self.assertEqual(1, result["reached_counts"]["1R"])

    def test_path_row_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stats = root / "stats.csv"
            trades = root / "trades.csv"
            stats.write_text(
                "status;trades_opened;trades_closed;csv_trade_rows;path_rows;path_calc_failures\n"
                "FINAL;1;1;1;0;0\n",
                encoding="utf-8",
            )
            trades.write_text(";".join(trade_path_validate.REQUIRED_PATH_COLUMNS) + "\n", encoding="utf-8")
            with self.assertRaises(trade_path_validate.TradePathError):
                trade_path_validate.validate_paths(stats, trades)


if __name__ == "__main__":
    unittest.main()
