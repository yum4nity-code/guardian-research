from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from binance_collector_v1 import (
    BinanceJsonlRecorder,
    normalize_force_order_message,
    normalize_funding,
    normalize_open_interest,
    normalize_perp_price,
    normalize_spot_price,
)


class BinanceCollectorV1Tests(unittest.TestCase):
    def test_core_rest_normalizers(self):
        received = 1_800_000_000_000

        spot = normalize_spot_price({"symbol": "BTCUSDT", "price": "80000.5"}, "BTCUSD", received)[0]
        self.assertEqual(spot["venue"], "BINANCE")
        self.assertEqual(spot["market_type"], "spot")
        self.assertEqual(spot["metric"], "last_price")
        self.assertEqual(spot["source_ts_ms"], received)
        self.assertIn("no server timestamp", spot["quality"]["reason"])

        perp = normalize_perp_price({"symbol": "BTCUSDT", "price": "79990.0", "time": received - 2}, "BTCUSD", received)[0]
        self.assertEqual(perp["value"], 79990.0)
        self.assertEqual(perp["source_ts_ms"], received - 2)

        oi = normalize_open_interest({"symbol": "BTCUSDT", "openInterest": "12345.67", "time": received - 3}, "BTCUSD", received)[0]
        self.assertEqual(oi["metric"], "open_interest")
        self.assertEqual(oi["unit"], "BTC")

        funding = normalize_funding({"symbol": "BTCUSDT", "lastFundingRate": "0.000123", "time": received - 4}, "BTCUSD", received)[0]
        self.assertEqual(funding["metric"], "funding_rate")
        self.assertAlmostEqual(funding["value"], 0.000123)

    def test_force_order_side_mapping_and_sampled_semantics(self):
        received = 1_800_000_000_000
        sell = {
            "stream": "btcusdt@forceOrder",
            "data": {
                "e": "forceOrder",
                "E": received - 1,
                "o": {
                    "s": "BTCUSDT",
                    "S": "SELL",
                    "q": "0.5",
                    "z": "0.4",
                    "p": "80000",
                    "ap": "79950",
                    "T": received - 2,
                },
            },
        }
        rows = normalize_force_order_message(sell, received)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["side"], "long")  # forced SELL closes long
        self.assertEqual(rows[1]["side"], "long")
        self.assertAlmostEqual(rows[1]["value"], 0.4 * 79950)
        self.assertIn("snapshot", rows[1]["unit"])
        self.assertIn("not exhaustive", rows[1]["quality"]["reason"])

        buy = json.loads(json.dumps(sell))
        buy["data"]["o"]["S"] = "BUY"
        buy["data"]["o"]["T"] = received - 1
        rows2 = normalize_force_order_message(buy, received)
        self.assertEqual(rows2[0]["side"], "short")

    def test_binance_recorder_uses_separate_filename(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                rec = BinanceJsonlRecorder(td_path)
                row = normalize_spot_price({"symbol": "ETHUSDT", "price": "2500"}, "ETHUSD", 1_800_000_000_000)[0]
                written = await rec.write([row, row])
                self.assertEqual(written, 1)
                files = list(td_path.glob("binance_eib_v1_*.jsonl"))
                self.assertEqual(len(files), 1)
                self.assertFalse(any(td_path.glob("bybit_eib_v1_*.jsonl")))
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
