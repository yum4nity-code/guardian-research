from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from collector_v1 import normalize_linear_ticker, normalize_liquidation_message, normalize_spot_ticker
from replay_v1 import ReplayReader


class NormalizationTests(unittest.TestCase):
    def test_spot_ticker(self):
        payload = {
            "retCode": 0,
            "time": 1_700_000_000_000,
            "result": {"category": "spot", "list": [{"symbol": "BTCUSDT", "lastPrice": "65000.5"}]},
        }
        recs = normalize_spot_ticker(payload, "BTCUSD", 1_700_000_000_250)
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["metric"], "last_price")
        self.assertEqual(r["market_type"], "spot")
        self.assertEqual(r["value"], 65000.5)
        self.assertEqual(r["available_at_ms"], 1_700_000_000_250)

    def test_linear_ticker_has_price_oi_funding(self):
        payload = {
            "retCode": 0,
            "time": 1_700_000_010_000,
            "result": {
                "category": "linear",
                "list": [{
                    "symbol": "ETHUSDT",
                    "lastPrice": "3300.1",
                    "openInterest": "123456.7",
                    "fundingRate": "0.0001",
                }],
            },
        }
        recs = normalize_linear_ticker(payload, "ETHUSD", 1_700_000_010_120)
        metrics = {r["metric"]: r for r in recs}
        self.assertEqual(set(metrics), {"last_price", "open_interest", "funding_rate"})
        self.assertEqual(metrics["open_interest"]["unit"], "ETH")
        self.assertAlmostEqual(metrics["funding_rate"]["value"], 0.0001)

    def test_liquidation_side_semantics_and_notional(self):
        payload = {
            "topic": "allLiquidation.BTCUSDT",
            "type": "snapshot",
            "ts": 1_700_000_020_500,
            "data": [{"T": 1_700_000_020_400, "s": "BTCUSDT", "S": "Buy", "v": "0.5", "p": "60000"}],
        }
        recs = normalize_liquidation_message(payload, 1_700_000_020_650)
        metrics = {r["metric"]: r for r in recs}
        self.assertEqual(metrics["liquidation_qty"]["side"], "long")
        self.assertEqual(metrics["liquidation_notional"]["value"], 30000.0)
        self.assertEqual(metrics["liquidation_notional"]["unit"], "USDT_est_bankruptcy_price")


class ReplayTests(unittest.TestCase):
    def test_replay_uses_available_at_not_source_ts(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.jsonl"
            rows = [
                {"event_id": "a", "source_ts_ms": 1000, "available_at_ms": 2000},
                {"event_id": "b", "source_ts_ms": 1500, "available_at_ms": 3000},
            ]
            p.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
            rr = ReplayReader([p])
            self.assertEqual(rr.pop_available(1999), [])
            self.assertEqual([x["event_id"] for x in rr.pop_available(2500)], ["a"])
            self.assertEqual([x["event_id"] for x in rr.pop_available(3000)], ["b"])


if __name__ == "__main__":
    unittest.main()
