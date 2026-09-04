from __future__ import annotations

import unittest

from market_state_multivenue_v1 import MultiVenueMarketStateEngine, build_cross_venue_symbol


def symbol_snapshot(
    *,
    status="OK",
    spot=100.0,
    perp=99.9,
    funding=0.0001,
    basis=-0.1,
    oi1=1.0,
    oi5=2.0,
    spot1=0.2,
    spot5=0.5,
    perp1=0.3,
    perp5=0.6,
    long1=0.0,
    long5=100.0,
    short1=50.0,
    short5=50.0,
):
    return {
        "quality": {"status": status},
        "raw": {
            "spot_last": spot,
            "perp_last": perp,
            "funding_rate": funding,
            "basis_pct": basis,
        },
        "returns_pct": {
            "spot": {"1m": spot1, "5m": spot5, "15m": None, "1h": None},
            "perpetual": {"1m": perp1, "5m": perp5, "15m": None, "1h": None},
            "perp_minus_spot_pp": {
                "1m": perp1 - spot1,
                "5m": perp5 - spot5,
                "15m": None,
                "1h": None,
            },
        },
        "open_interest_change_pct": {"1m": oi1, "5m": oi5, "15m": None, "1h": None},
        "liquidation_notional_usdt_est": {
            "long": {"1m": long1, "5m": long5, "15m": None, "1h": None},
            "short": {"1m": short1, "5m": short5, "15m": None, "1h": None},
        },
    }


class MultiVenueStateTests(unittest.TestCase):
    def test_cross_venue_keeps_venue_specific_liquidations(self):
        bybit = symbol_snapshot(long1=100, short1=0)
        binance = symbol_snapshot(long1=200, short1=0, spot=100.1, perp=100.0, funding=0.0002, oi1=3.0)
        cross = build_cross_venue_symbol(bybit, binance)

        self.assertTrue(cross["quality"]["both_core_ok"])
        self.assertEqual(cross["liquidation_confirmation"]["bybit_long_observed"]["1m"], 100)
        self.assertEqual(cross["liquidation_confirmation"]["binance_long_observed"]["1m"], 200)
        self.assertEqual(cross["liquidation_confirmation"]["long_active_venues"]["1m"], 2)
        self.assertNotIn("total", cross["liquidation_confirmation"])
        self.assertIn("not exhaustive", cross["liquidation_confirmation"]["semantics"])

    def test_cross_venue_oi_mean_and_dispersion(self):
        bybit = symbol_snapshot(oi1=-1.0)
        binance = symbol_snapshot(oi1=-3.0)
        cross = build_cross_venue_symbol(bybit, binance)
        self.assertEqual(cross["open_interest_change_pct"]["mean"]["1m"], -2.0)
        self.assertEqual(cross["open_interest_change_pct"]["dispersion_pp"]["1m"], 2.0)
        self.assertTrue(cross["open_interest_change_pct"]["same_direction"]["1m"])

    def test_engine_never_mixes_raw_venue_series(self):
        engine = MultiVenueMarketStateEngine()
        t = 1_800_000_000_000
        bybit_rec = {
            "canonical_symbol": "BTCUSD",
            "venue": "BYBIT",
            "market_type": "spot",
            "metric": "last_price",
            "available_at_ms": t,
            "value": 100.0,
        }
        binance_rec = {
            "canonical_symbol": "BTCUSD",
            "venue": "BINANCE",
            "market_type": "spot",
            "metric": "last_price",
            "available_at_ms": t,
            "value": 101.0,
        }
        self.assertTrue(engine.ingest(bybit_rec, as_of_ms=t))
        self.assertTrue(engine.ingest(binance_rec, as_of_ms=t))
        snap = engine.snapshot(as_of_ms=t, generation_id=1)
        self.assertEqual(snap["venues"]["BYBIT"]["symbols"]["BTCUSD"]["raw"]["spot_last"], 100.0)
        self.assertEqual(snap["venues"]["BINANCE"]["symbols"]["BTCUSD"]["raw"]["spot_last"], 101.0)
        self.assertAlmostEqual(
            snap["cross_venue"]["BTCUSD"]["price_spread_pct"]["binance_minus_bybit_spot"],
            1.0,
        )
        self.assertEqual(snap["research_guardrail"], "NO_STRATEGY_DECISION_OUTPUT")


if __name__ == "__main__":
    unittest.main()
