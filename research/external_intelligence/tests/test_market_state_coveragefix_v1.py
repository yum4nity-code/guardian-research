from __future__ import annotations

import unittest

from market_state_v1_coveragefix import build_coverage_snapshot_from_records

BASE = 1_700_000_000_000


def rec(symbol, market_type, metric, ts_ms, value, side=None, reason=None):
    row = {
        "canonical_symbol": symbol,
        "market_type": market_type,
        "metric": metric,
        "available_at_ms": ts_ms,
        "value": value,
        "side": side,
    }
    if reason is not None:
        row["quality"] = {"reason": reason}
    return row


def ok_health(ts_ms, symbol="BTCUSD"):
    return rec(
        symbol,
        "aggregate",
        "health",
        ts_ms,
        "OK",
        reason="spot:ok:1000ms;perpetual:ok:1000ms;liq_ws:connected",
    )


class CoverageFixTests(unittest.TestCase):
    def test_old_anchor_does_not_masquerade_as_5m_return(self):
        rows = [
            rec("BTCUSD", "spot", "last_price", BASE, 100.0),
            rec("BTCUSD", "spot", "last_price", BASE + 60_000, 101.0),
            rec("BTCUSD", "spot", "last_price", BASE + 15 * 60_000, 105.0),
        ]
        snap = build_coverage_snapshot_from_records(
            rows, as_of_ms=BASE + 15 * 60_000
        )
        btc = snap["symbols"]["BTCUSD"]
        self.assertIsNone(btc["returns_pct"]["spot"]["5m"])
        self.assertFalse(btc["coverage"]["spot_return"]["5m"]["complete"])
        self.assertGreater(
            btc["coverage"]["spot_return"]["5m"]["anchor_gap_ms"], 15_000
        )

    def test_fresh_boundary_anchor_produces_return(self):
        rows = [
            rec("BTCUSD", "spot", "last_price", BASE, 100.0),
            rec("BTCUSD", "spot", "last_price", BASE + 5 * 60_000, 102.0),
            rec("BTCUSD", "spot", "last_price", BASE + 10 * 60_000, 104.0),
        ]
        snap = build_coverage_snapshot_from_records(
            rows, as_of_ms=BASE + 10 * 60_000
        )
        btc = snap["symbols"]["BTCUSD"]
        self.assertTrue(btc["coverage"]["spot_return"]["5m"]["complete"])
        self.assertAlmostEqual(
            btc["returns_pct"]["spot"]["5m"], (104.0 / 102.0 - 1.0) * 100.0
        )

    def test_liquidation_zero_requires_continuous_health_coverage(self):
        rows = []
        for minute in range(0, 7):
            rows.append(ok_health(BASE + minute * 60_000))
        snap = build_coverage_snapshot_from_records(
            rows, as_of_ms=BASE + 6 * 60_000
        )
        btc = snap["symbols"]["BTCUSD"]
        self.assertTrue(btc["coverage"]["liquidation"]["5m"]["complete"])
        self.assertEqual(
            btc["liquidation_notional_usdt_est"]["long"]["5m"], 0
        )
        self.assertEqual(
            btc["liquidation_notional_usdt_est"]["short"]["5m"], 0
        )

    def test_liquidation_window_is_null_across_collection_gap(self):
        rows = [
            ok_health(BASE),
            ok_health(BASE + 60_000),
            # deliberate 4-minute hole
            ok_health(BASE + 5 * 60_000),
            ok_health(BASE + 6 * 60_000),
            rec(
                "BTCUSD",
                "perpetual",
                "liquidation_notional",
                BASE + 5 * 60_000 + 10_000,
                2500.0,
                side="long",
            ),
        ]
        snap = build_coverage_snapshot_from_records(
            rows, as_of_ms=BASE + 6 * 60_000
        )
        btc = snap["symbols"]["BTCUSD"]
        self.assertFalse(btc["coverage"]["liquidation"]["5m"]["complete"])
        self.assertIsNone(
            btc["liquidation_notional_usdt_est"]["long"]["5m"]
        )
        self.assertIsNone(
            btc["liquidation_notional_usdt_est"]["net_short_minus_long"]["5m"]
        )

    def test_down_health_breaks_liquidation_coverage(self):
        rows = [
            ok_health(BASE),
            ok_health(BASE + 60_000),
            rec(
                "BTCUSD",
                "aggregate",
                "health",
                BASE + 2 * 60_000,
                "PARTIAL",
                reason="spot:ok:1000ms;perpetual:ok:1000ms;liq_ws:down",
            ),
            ok_health(BASE + 3 * 60_000),
            ok_health(BASE + 4 * 60_000),
            ok_health(BASE + 5 * 60_000),
        ]
        snap = build_coverage_snapshot_from_records(
            rows, as_of_ms=BASE + 5 * 60_000
        )
        btc = snap["symbols"]["BTCUSD"]
        self.assertFalse(btc["coverage"]["liquidation"]["5m"]["complete"])
        self.assertIsNone(
            btc["liquidation_notional_usdt_est"]["long"]["5m"]
        )

    def test_future_observation_remains_hidden(self):
        rows = [
            rec("BTCUSD", "spot", "last_price", BASE, 100.0),
            rec("BTCUSD", "spot", "last_price", BASE + 60_000, 999.0),
        ]
        snap = build_coverage_snapshot_from_records(rows, as_of_ms=BASE)
        btc = snap["symbols"]["BTCUSD"]
        self.assertEqual(btc["raw"]["spot_last"], 100.0)
        self.assertEqual(btc["quality"]["latest_available_at_ms"], BASE)


if __name__ == "__main__":
    unittest.main()
