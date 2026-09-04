from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from market_state_v1 import MarketStateService, build_snapshot_from_records

BASE = 1_700_000_000_000


def rec(symbol, market_type, metric, ts_ms, value, side=None):
    return {
        "canonical_symbol": symbol,
        "market_type": market_type,
        "metric": metric,
        "available_at_ms": ts_ms,
        "value": value,
        "side": side,
    }


class MarketStateTests(unittest.TestCase):
    def test_future_record_is_hidden_and_returns_are_availability_gated(self):
        rows = [
            rec("BTCUSD", "spot", "last_price", BASE, 100.0),
            rec("BTCUSD", "perpetual", "last_price", BASE, 101.0),
            rec("BTCUSD", "perpetual", "open_interest", BASE, 1000.0),
            rec("BTCUSD", "perpetual", "funding_rate", BASE, 0.0001),
            rec("BTCUSD", "aggregate", "health", BASE, "OK"),
            rec("BTCUSD", "spot", "last_price", BASE + 60_000, 102.0),
            rec("BTCUSD", "perpetual", "last_price", BASE + 60_000, 104.03),
            rec("BTCUSD", "perpetual", "open_interest", BASE + 60_000, 1100.0),
            rec("BTCUSD", "spot", "last_price", BASE + 120_000, 999.0),
        ]
        snap = build_snapshot_from_records(rows, as_of_ms=BASE + 60_000)
        btc = snap["symbols"]["BTCUSD"]
        self.assertEqual(btc["raw"]["spot_last"], 102.0)
        self.assertAlmostEqual(btc["returns_pct"]["spot"]["1m"], 2.0)
        self.assertAlmostEqual(btc["open_interest_change_pct"]["1m"], 10.0)
        self.assertEqual(btc["quality"]["status"], "OK")
        self.assertEqual(btc["quality"]["latest_available_at_ms"], BASE + 60_000)

    def test_basis_and_liquidation_windows(self):
        rows = [
            rec("BTCUSD", "spot", "last_price", BASE, 100.0),
            rec("BTCUSD", "perpetual", "last_price", BASE, 101.0),
            rec("BTCUSD", "perpetual", "liquidation_notional", BASE + 10_000, 5000.0, "long"),
            rec("BTCUSD", "perpetual", "liquidation_notional", BASE + 20_000, 2000.0, "short"),
        ]
        snap = build_snapshot_from_records(rows, as_of_ms=BASE + 30_000)
        btc = snap["symbols"]["BTCUSD"]
        self.assertAlmostEqual(btc["raw"]["basis_pct"], 1.0)
        self.assertEqual(btc["liquidation_notional_usdt_est"]["long"]["1m"], 5000.0)
        self.assertEqual(btc["liquidation_notional_usdt_est"]["short"]["1m"], 2000.0)
        self.assertEqual(btc["liquidation_notional_usdt_est"]["net_short_minus_long"]["1m"], -3000.0)

    def test_insufficient_history_stays_null_instead_of_forward_filling(self):
        rows = [
            rec("ETHUSD", "spot", "last_price", BASE, 3000.0),
            rec("ETHUSD", "spot", "last_price", BASE + 60_000, 3030.0),
        ]
        snap = build_snapshot_from_records(rows, as_of_ms=BASE + 60_000)
        eth = snap["symbols"]["ETHUSD"]
        self.assertIsNotNone(eth["returns_pct"]["spot"]["1m"])
        self.assertIsNone(eth["returns_pct"]["spot"]["5m"])
        self.assertIsNone(eth["returns_pct"]["spot"]["15m"])
        self.assertIsNone(eth["returns_pct"]["spot"]["1h"])

    def test_service_writes_atomic_shared_snapshot_and_generation_increases(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            day = datetime.fromtimestamp(BASE / 1000, tz=timezone.utc).strftime("%Y%m%d")
            data_path = data_dir / f"bybit_eib_v1_{day}.jsonl"
            rows = [
                rec("BTCUSD", "spot", "last_price", BASE, 100.0),
                rec("BTCUSD", "perpetual", "last_price", BASE, 101.0),
                rec("BTCUSD", "perpetual", "open_interest", BASE, 1000.0),
                rec("BTCUSD", "perpetual", "funding_rate", BASE, 0.0001),
            ]
            data_path.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
            (data_dir / "health.json").write_text(
                json.dumps({
                    "updated_at_ms": BASE,
                    "symbols": {"BTCUSD": {"status": "OK", "reason": "synthetic"}},
                }),
                encoding="utf-8",
            )
            service = MarketStateService(data_dir)
            first = service.publish_once(BASE + 1_000)
            second = service.publish_once(BASE + 2_000)
            self.assertGreater(second["generation_id"], first["generation_id"])
            disk = json.loads((data_dir / "market_state_v1.json").read_text(encoding="utf-8"))
            self.assertEqual(disk["generation_id"], second["generation_id"])
            self.assertEqual(disk["symbols"]["BTCUSD"]["quality"]["status"], "OK")


if __name__ == "__main__":
    unittest.main()
