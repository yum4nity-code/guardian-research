from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from mt5_common_bridge_multivenue_v1 import FIELDS, flatten_snapshot, publish_once


def _sym(status: str, spot: float, perp: float, oi: float, funding: float, basis: float) -> dict:
    return {
        "quality": {"status": status, "core_age_ms": 100},
        "raw": {
            "spot_last": spot,
            "perp_last": perp,
            "open_interest": oi,
            "funding_rate": funding,
            "basis_pct": basis,
        },
        "coverage": {
            "spot_return": {"1m": {"complete": True}, "5m": {"complete": False}},
            "perpetual_return": {"1m": {"complete": True}, "5m": {"complete": False}},
            "open_interest_change": {"1m": {"complete": True}, "5m": {"complete": False}},
            "liquidation": {"1m": {"complete": True}, "5m": {"complete": False}},
        },
    }


def sample_snapshot() -> dict:
    cross = {}
    for symbol in ("BTCUSD", "ETHUSD"):
        cross[symbol] = {
            "quality": {"both_core_ok": True},
            "price_spread_pct": {
                "binance_minus_bybit_spot": 0.01,
                "binance_minus_bybit_perp": 0.02,
            },
            "funding": {"bybit": 0.0001, "binance": 0.0002, "binance_minus_bybit_fraction": 0.0001},
            "basis": {"bybit_pct": -0.03, "binance_pct": -0.04, "binance_minus_bybit_pp": -0.01},
            "open_interest_change_pct": {
                "mean": {"1m": -0.1, "5m": None},
                "dispersion_pp": {"1m": 0.02, "5m": None},
                "same_direction": {"1m": True, "5m": None},
            },
            "returns_pct": {
                "spot_mean": {"1m": -0.2, "5m": None},
                "perp_mean": {"1m": -0.18, "5m": None},
                "dislocation_mean": {"1m": 0.02, "5m": None},
            },
            "liquidation_confirmation": {
                "bybit_long_observed": {"1m": 100.0, "5m": None},
                "binance_long_observed": {"1m": 200.0, "5m": None},
                "bybit_short_observed": {"1m": 0.0, "5m": None},
                "binance_short_observed": {"1m": 0.0, "5m": None},
                "long_active_venues": {"1m": 2, "5m": None},
                "short_active_venues": {"1m": 0, "5m": None},
            },
        }
    return {
        "schema_version": 1,
        "engine": "guardian-market-state-multivenue-v1",
        "generation_id": 123456,
        "computed_at_ms": 123450,
        "research_guardrail": "NO_STRATEGY_DECISION_OUTPUT",
        "venues": {
            "BYBIT": {"symbols": {"BTCUSD": _sym("OK", 80000, 79990, 100, 0.0001, -0.03), "ETHUSD": _sym("OK", 2500, 2499, 200, 0.0001, -0.04)}},
            "BINANCE": {"symbols": {"BTCUSD": _sym("OK", 80008, 80006, 110, 0.0002, -0.04), "ETHUSD": _sym("OK", 2501, 2500, 210, 0.0002, -0.05)}},
        },
        "cross_venue": cross,
    }


class MultiVenueBridgeTests(unittest.TestCase):
    def test_flatten_keeps_venues_and_cross_facts(self):
        rows = flatten_snapshot(sample_snapshot())
        self.assertEqual(len(rows), 2)
        btc = rows[0]
        self.assertEqual(btc["symbol"], "BTCUSD")
        self.assertEqual(btc["bybit_spot_last"], "80000")
        self.assertEqual(btc["binance_spot_last"], "80008")
        self.assertEqual(btc["both_core_ok"], "1")
        self.assertEqual(btc["long_active_venues_1m"], "2")
        self.assertEqual(btc["oi_same_direction_1m"], "1")
        self.assertEqual(btc["oi_mean_5m"], "")
        self.assertEqual(set(btc), set(FIELDS))

    def test_publish_once_writes_two_ascii_csv_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "market_state_multivenue_v1.json"
            output = root / "common" / "market_state_multivenue_v1.csv"
            source.write_text(json.dumps(sample_snapshot()), encoding="utf-8")
            result = publish_once(source, output)
            self.assertEqual(result["generation_id"], 123456)
            with output.open("r", encoding="ascii", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual([r["symbol"] for r in rows], ["BTCUSD", "ETHUSD"])
            self.assertTrue(all(r["bridge_schema_version"] == "2" for r in rows))

    def test_publish_rejects_strategy_guardrail_loss(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "bad.json"
            output = root / "out.csv"
            snap = sample_snapshot()
            snap["research_guardrail"] = "BUY_BTC"
            source.write_text(json.dumps(snap), encoding="utf-8")
            with self.assertRaises(ValueError):
                publish_once(source, output)


if __name__ == "__main__":
    unittest.main()
