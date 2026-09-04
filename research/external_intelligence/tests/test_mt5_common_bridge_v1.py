from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from mt5_common_bridge_v1 import FIELDS, flatten_snapshot, publish_once


class MT5CommonBridgeTests(unittest.TestCase):
    def _snapshot(self):
        return {
            "schema_version": 1,
            "engine": "guardian-market-state-v1",
            "generation_id": 123456,
            "computed_at_ms": 123450,
            "symbols": {
                "BTCUSD": {
                    "quality": {"status": "OK", "core_age_ms": 1200},
                    "raw": {"spot_last": 100.0, "perp_last": 99.9, "open_interest": 5000.0, "funding_rate": 0.0001, "basis_pct": -0.1},
                    "returns_pct": {"spot": {"1m": 0.1, "5m": None}, "perpetual": {"1m": 0.2, "5m": None}, "perp_minus_spot_pp": {"1m": 0.1, "5m": None}},
                    "open_interest_change_pct": {"1m": 1.2, "5m": None},
                    "liquidation_notional_usdt_est": {"long": {"1m": 0, "5m": None}, "short": {"1m": 50, "5m": None}, "net_short_minus_long": {"1m": 50, "5m": None}},
                    "coverage": {
                        "spot_return": {"1m": {"complete": True}, "5m": {"complete": False}},
                        "perpetual_return": {"1m": {"complete": True}, "5m": {"complete": False}},
                        "open_interest_change": {"1m": {"complete": True}, "5m": {"complete": False}},
                        "liquidation": {"1m": {"complete": True}, "5m": {"complete": False}},
                    },
                },
                "ETHUSD": {
                    "quality": {"status": "OK", "core_age_ms": 900},
                    "raw": {"spot_last": 10.0, "perp_last": 10.0, "open_interest": 9000.0, "funding_rate": 0.0002, "basis_pct": 0.0},
                    "returns_pct": {"spot": {"1m": None, "5m": None}, "perpetual": {"1m": None, "5m": None}, "perp_minus_spot_pp": {"1m": None, "5m": None}},
                    "open_interest_change_pct": {"1m": None, "5m": None},
                    "liquidation_notional_usdt_est": {"long": {"1m": None, "5m": None}, "short": {"1m": None, "5m": None}, "net_short_minus_long": {"1m": None, "5m": None}},
                    "coverage": {
                        "spot_return": {"1m": {"complete": False}, "5m": {"complete": False}},
                        "perpetual_return": {"1m": {"complete": False}, "5m": {"complete": False}},
                        "open_interest_change": {"1m": {"complete": False}, "5m": {"complete": False}},
                        "liquidation": {"1m": {"complete": False}, "5m": {"complete": False}},
                    },
                },
            },
        }

    def test_null_is_empty_and_zero_is_preserved(self):
        rows = flatten_snapshot(self._snapshot())
        btc = rows[0]
        self.assertEqual(btc["long_liq_1m"], "0")
        self.assertEqual(btc["long_liq_5m"], "")
        self.assertEqual(btc["cov_liq_1m"], "1")
        self.assertEqual(btc["cov_liq_5m"], "0")

    def test_atomic_csv_has_two_symbols_and_expected_schema(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "state.json"
            out = td / "common" / "GuardianSharedIntelligence" / "market_state_v1.csv"
            src.write_text(json.dumps(self._snapshot()), encoding="utf-8")
            result = publish_once(src, out)
            self.assertEqual(result["generation_id"], 123456)
            with out.open("r", encoding="ascii", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(list(rows[0].keys()), FIELDS)
            self.assertEqual([r["symbol"] for r in rows], ["BTCUSD", "ETHUSD"])
            self.assertEqual(rows[0]["generation_id"], rows[1]["generation_id"])


if __name__ == "__main__":
    unittest.main()
