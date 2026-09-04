#!/usr/bin/env python3
"""Guardian multi-venue market-state V1 candidate.

Consumes the already-separated Bybit and Binance EIB V1 streams and preserves
venue identity all the way through feature computation. It deliberately does
NOT mix raw observations from different venues into one time series.

Output is research-only and strategy-neutral. No BUY/SELL decisions.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from market_state_v1 import IncrementalFileReader, now_ms, write_atomic_json
from market_state_v1_coveragefix import MarketStateEngineCoverageFixed

VENUES = ("BYBIT", "BINANCE")
SYMBOLS = ("BTCUSD", "ETHUSD")
WINDOWS = ("1m", "5m", "15m", "1h")


def _mean_two(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return (a + b) / 2.0


def _spread(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return b - a


def _ratio_spread_pct(bybit: float | None, binance: float | None) -> float | None:
    if bybit is None or binance is None or bybit == 0:
        return None
    return (binance / bybit - 1.0) * 100.0


def _same_direction(a: float | None, b: float | None) -> bool | None:
    if a is None or b is None:
        return None
    if a == 0 or b == 0:
        return a == b
    return (a > 0) == (b > 0)


def _get(d: dict[str, Any], *path: str) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _liq_active(value: float | None) -> int | None:
    if value is None:
        return None
    return 1 if value > 0 else 0


def build_cross_venue_symbol(bybit: dict[str, Any], binance: dict[str, Any]) -> dict[str, Any]:
    """Build transparent cross-venue facts without pretending incompatible data are identical."""
    out: dict[str, Any] = {
        "quality": {
            "bybit_status": _get(bybit, "quality", "status"),
            "binance_status": _get(binance, "quality", "status"),
        },
        "price_spread_pct": {},
        "funding": {},
        "basis": {},
        "returns_pct": {"spot_mean": {}, "perp_mean": {}, "dislocation_mean": {}},
        "open_interest_change_pct": {"mean": {}, "dispersion_pp": {}, "same_direction": {}},
        "liquidation_confirmation": {
            "long_active_venues": {},
            "short_active_venues": {},
            "bybit_long_observed": {},
            "binance_long_observed": {},
            "bybit_short_observed": {},
            "binance_short_observed": {},
            "semantics": (
                "Do not interpret as exhaustive cross-venue liquidation volume. "
                "Binance forceOrder is a sampled snapshot feed (latest force order per symbol per 1000ms); "
                "Bybit and Binance liquidation notionals therefore remain venue-specific observed measures."
            ),
        },
    }
    out["quality"]["both_core_ok"] = (
        out["quality"]["bybit_status"] == "OK" and out["quality"]["binance_status"] == "OK"
    )

    bybit_spot = _get(bybit, "raw", "spot_last")
    binance_spot = _get(binance, "raw", "spot_last")
    bybit_perp = _get(bybit, "raw", "perp_last")
    binance_perp = _get(binance, "raw", "perp_last")
    out["price_spread_pct"] = {
        "binance_minus_bybit_spot": _ratio_spread_pct(bybit_spot, binance_spot),
        "binance_minus_bybit_perp": _ratio_spread_pct(bybit_perp, binance_perp),
    }

    bybit_funding = _get(bybit, "raw", "funding_rate")
    binance_funding = _get(binance, "raw", "funding_rate")
    out["funding"] = {
        "bybit": bybit_funding,
        "binance": binance_funding,
        "binance_minus_bybit_fraction": _spread(bybit_funding, binance_funding),
    }

    bybit_basis = _get(bybit, "raw", "basis_pct")
    binance_basis = _get(binance, "raw", "basis_pct")
    out["basis"] = {
        "bybit_pct": bybit_basis,
        "binance_pct": binance_basis,
        "binance_minus_bybit_pp": _spread(bybit_basis, binance_basis),
    }

    for window in WINDOWS:
        b_spot_ret = _get(bybit, "returns_pct", "spot", window)
        n_spot_ret = _get(binance, "returns_pct", "spot", window)
        b_perp_ret = _get(bybit, "returns_pct", "perpetual", window)
        n_perp_ret = _get(binance, "returns_pct", "perpetual", window)
        b_dis = _get(bybit, "returns_pct", "perp_minus_spot_pp", window)
        n_dis = _get(binance, "returns_pct", "perp_minus_spot_pp", window)
        out["returns_pct"]["spot_mean"][window] = _mean_two(b_spot_ret, n_spot_ret)
        out["returns_pct"]["perp_mean"][window] = _mean_two(b_perp_ret, n_perp_ret)
        out["returns_pct"]["dislocation_mean"][window] = _mean_two(b_dis, n_dis)

        b_oi = _get(bybit, "open_interest_change_pct", window)
        n_oi = _get(binance, "open_interest_change_pct", window)
        out["open_interest_change_pct"]["mean"][window] = _mean_two(b_oi, n_oi)
        out["open_interest_change_pct"]["dispersion_pp"][window] = (
            None if b_oi is None or n_oi is None else abs(n_oi - b_oi)
        )
        out["open_interest_change_pct"]["same_direction"][window] = _same_direction(b_oi, n_oi)

        b_long = _get(bybit, "liquidation_notional_usdt_est", "long", window)
        n_long = _get(binance, "liquidation_notional_usdt_est", "long", window)
        b_short = _get(bybit, "liquidation_notional_usdt_est", "short", window)
        n_short = _get(binance, "liquidation_notional_usdt_est", "short", window)
        out["liquidation_confirmation"]["bybit_long_observed"][window] = b_long
        out["liquidation_confirmation"]["binance_long_observed"][window] = n_long
        out["liquidation_confirmation"]["bybit_short_observed"][window] = b_short
        out["liquidation_confirmation"]["binance_short_observed"][window] = n_short

        long_flags = (_liq_active(b_long), _liq_active(n_long))
        short_flags = (_liq_active(b_short), _liq_active(n_short))
        out["liquidation_confirmation"]["long_active_venues"][window] = (
            None if None in long_flags else int(long_flags[0]) + int(long_flags[1])
        )
        out["liquidation_confirmation"]["short_active_venues"][window] = (
            None if None in short_flags else int(short_flags[0]) + int(short_flags[1])
        )

    return out


class MultiVenueMarketStateEngine:
    def __init__(self) -> None:
        self.engines = {venue: MarketStateEngineCoverageFixed() for venue in VENUES}

    def ingest(self, rec: dict[str, Any], *, as_of_ms: int | None = None) -> bool:
        venue = str(rec.get("venue") or "").upper()
        engine = self.engines.get(venue)
        if engine is None:
            return False
        return engine.ingest(rec, as_of_ms=as_of_ms)

    def snapshot(
        self,
        *,
        as_of_ms: int,
        generation_id: int,
        live_health_by_venue: dict[str, dict[str, Any] | None] | None = None,
    ) -> dict[str, Any]:
        live_health_by_venue = live_health_by_venue or {}
        venue_snapshots: dict[str, Any] = {}
        for venue, engine in self.engines.items():
            venue_snapshots[venue] = engine.snapshot(
                as_of_ms=as_of_ms,
                generation_id=generation_id,
                live_health=live_health_by_venue.get(venue),
            )

        cross: dict[str, Any] = {}
        for symbol in SYMBOLS:
            bybit = venue_snapshots["BYBIT"]["symbols"][symbol]
            binance = venue_snapshots["BINANCE"]["symbols"][symbol]
            cross[symbol] = build_cross_venue_symbol(bybit, binance)

        return {
            "schema_version": 1,
            "engine": "guardian-market-state-multivenue-v1",
            "generation_id": int(generation_id),
            "computed_at_ms": int(as_of_ms),
            "computed_at_utc": datetime.fromtimestamp(as_of_ms / 1000, tz=timezone.utc).isoformat(),
            "venues": venue_snapshots,
            "cross_venue": cross,
            "research_guardrail": "NO_STRATEGY_DECISION_OUTPUT",
        }


def _daily_paths(data_dir: Path, prefix: str, at_ms: int) -> list[Path]:
    dt = datetime.fromtimestamp(at_ms / 1000, tz=timezone.utc)
    return [
        data_dir / f"{prefix}_{day.strftime('%Y%m%d')}.jsonl"
        for day in (dt - timedelta(days=1), dt)
    ]


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


class MultiVenueMarketStateService:
    def __init__(
        self,
        data_dir: Path,
        *,
        snapshot_name: str = "market_state_multivenue_v1.json",
        interval_seconds: float = 1.0,
    ) -> None:
        self.data_dir = data_dir
        self.snapshot_path = data_dir / snapshot_name
        self.interval_seconds = max(0.25, interval_seconds)
        self.engine = MultiVenueMarketStateEngine()
        self.stop_event = asyncio.Event()
        self._readers: dict[Path, IncrementalFileReader] = {}
        self._last_generation = 0

    def _ensure_readers(self, at_ms: int) -> None:
        keep = set(_daily_paths(self.data_dir, "bybit_eib_v1", at_ms))
        keep.update(_daily_paths(self.data_dir, "binance_eib_v1", at_ms))
        for path in keep:
            self._readers.setdefault(path, IncrementalFileReader(path))
        for path in list(self._readers):
            if path not in keep:
                del self._readers[path]

    def ingest_available_files(self, at_ms: int) -> int:
        self._ensure_readers(at_ms)
        accepted = 0
        for reader in self._readers.values():
            for rec in reader.read_new():
                if self.engine.ingest(rec, as_of_ms=at_ms):
                    accepted += 1
        return accepted

    def publish_once(self, at_ms: int | None = None) -> dict[str, Any]:
        if at_ms is None:
            at_ms = now_ms()
        self.ingest_available_files(at_ms)
        generation = max(int(at_ms), self._last_generation + 1)
        live = {
            "BYBIT": _load_json(self.data_dir / "health.json"),
            "BINANCE": _load_json(self.data_dir / "binance_health.json"),
        }
        snapshot = self.engine.snapshot(
            as_of_ms=at_ms,
            generation_id=generation,
            live_health_by_venue=live,
        )
        write_atomic_json(self.snapshot_path, snapshot)
        self._last_generation = generation
        return snapshot

    async def run(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        while not self.stop_event.is_set():
            self.publish_once()
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                pass


if __name__ == "__main__":
    raise SystemExit("Use the dedicated smoke/gate launcher; this module is a research engine, not a standalone trading service.")
