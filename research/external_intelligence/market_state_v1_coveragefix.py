#!/usr/bin/env python3
"""Coverage-aware Guardian market-state V1 candidate.

This module keeps the validated market_state_v1 transport/feature engine intact
and fixes two research-integrity issues before any MT5/Guardian consumer is
allowed to use the shared features:

1) rolling price/OI changes must have a fresh observation near the requested
   historical boundary, instead of silently using a much older anchor;
2) liquidation sums are numeric (including zero) only when the liquidation
   websocket/health history demonstrates continuous coverage of the whole
   requested window. Otherwise the value is null.

No trading decisions are produced.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Deque, Iterable

from market_state_v1 import (
    MAX_HISTORY_MS,
    SYMBOLS,
    WINDOWS_MS,
    MarketStateEngine,
    MarketStateService,
)

# EIB REST cadence is 5 s in V1. Three cadences allow ordinary scheduling /
# network jitter but reject anchors from a previous collection session.
WINDOW_ANCHOR_TOLERANCE_MS = 15_000

# Health history is persisted on semantic change + once/minute heartbeat after
# the validated healthfix. 75 s accepts normal heartbeat jitter but fails gaps.
HEALTH_COVERAGE_MAX_GAP_MS = 75_000


class MarketStateEngineCoverageFixed(MarketStateEngine):
    """MarketStateEngine with explicit historical-window coverage semantics."""

    def __init__(self) -> None:
        super().__init__()
        self.health_history: dict[str, Deque[tuple[int, str, str]]] = {
            s: deque() for s in SYMBOLS
        }

    def ingest(self, rec: dict[str, Any], *, as_of_ms: int | None = None) -> bool:
        accepted = super().ingest(rec, as_of_ms=as_of_ms)
        if not accepted or rec.get("metric") != "health":
            return accepted

        symbol = str(rec.get("canonical_symbol") or "")
        if symbol not in self.health_history:
            return accepted
        try:
            ts_ms = int(rec["available_at_ms"])
        except (KeyError, TypeError, ValueError):
            return accepted
        status = str(rec.get("value") or "")
        quality = rec.get("quality") or {}
        reason = str(quality.get("reason") or "")
        row = (ts_ms, status, reason)
        hist = self.health_history[symbol]
        if hist and ts_ms < hist[-1][0]:
            rows = list(hist)
            rows.append(row)
            rows.sort(key=lambda x: x[0])
            hist.clear()
            hist.extend(rows)
        else:
            hist.append(row)
        return accepted

    def prune(self, as_of_ms: int) -> None:
        super().prune(as_of_ms)
        cutoff = as_of_ms - MAX_HISTORY_MS - HEALTH_COVERAGE_MAX_GAP_MS
        for hist in self.health_history.values():
            while len(hist) > 1 and hist[1][0] < cutoff:
                hist.popleft()

    @classmethod
    def _change_with_coverage(
        cls,
        series: Deque[tuple[int, float]],
        as_of_ms: int,
        window_ms: int,
    ) -> tuple[float | None, dict[str, Any]]:
        current = cls._latest_at_or_before(series, as_of_ms)
        target_ms = as_of_ms - window_ms
        anchor = cls._latest_at_or_before(series, target_ms)

        current_age_ms = None if current is None else max(0, as_of_ms - current[0])
        anchor_gap_ms = None if anchor is None else max(0, target_ms - anchor[0])
        complete = (
            current is not None
            and anchor is not None
            and current_age_ms is not None
            and current_age_ms <= WINDOW_ANCHOR_TOLERANCE_MS
            and anchor_gap_ms is not None
            and anchor_gap_ms <= WINDOW_ANCHOR_TOLERANCE_MS
        )
        value = None
        if complete and anchor is not None and current is not None and anchor[1] != 0:
            value = (current[1] / anchor[1] - 1.0) * 100.0
        return value, {
            "complete": bool(complete),
            "current_age_ms": current_age_ms,
            "anchor_gap_ms": anchor_gap_ms,
            "anchor_tolerance_ms": WINDOW_ANCHOR_TOLERANCE_MS,
        }

    def _health_rows_with_live(
        self,
        symbol: str,
        as_of_ms: int,
        live_health: dict[str, Any] | None,
    ) -> list[tuple[int, str, str]]:
        rows = [row for row in self.health_history[symbol] if row[0] <= as_of_ms]
        if live_health:
            try:
                updated_at_ms = int(live_health.get("updated_at_ms"))
            except (TypeError, ValueError):
                updated_at_ms = 0
            sym = (live_health.get("symbols") or {}).get(symbol) or {}
            status = str(sym.get("status") or "")
            reason = str(sym.get("reason") or "")
            if 0 < updated_at_ms <= as_of_ms and status:
                live_row = (updated_at_ms, status, reason)
                if not rows or rows[-1] != live_row:
                    rows.append(live_row)
        rows.sort(key=lambda x: x[0])
        return rows

    def _liquidation_coverage(
        self,
        symbol: str,
        as_of_ms: int,
        window_ms: int,
        live_health: dict[str, Any] | None,
    ) -> dict[str, Any]:
        start_ms = as_of_ms - window_ms
        rows = self._health_rows_with_live(symbol, as_of_ms, live_health)
        start_anchor = None
        for row in rows:
            if row[0] <= start_ms:
                start_anchor = row
            else:
                break
        end_anchor = rows[-1] if rows else None

        start_anchor_gap_ms = (
            None if start_anchor is None else max(0, start_ms - start_anchor[0])
        )
        end_age_ms = None if end_anchor is None else max(0, as_of_ms - end_anchor[0])

        segment: list[tuple[int, str, str]] = []
        if start_anchor is not None:
            segment.append(start_anchor)
        segment.extend(row for row in rows if start_ms < row[0] <= as_of_ms)

        max_gap_ms = None
        if len(segment) >= 2:
            max_gap_ms = max(b[0] - a[0] for a, b in zip(segment, segment[1:]))
        elif len(segment) == 1:
            max_gap_ms = 0

        all_connected = bool(segment) and all(
            status == "OK" and "liq_ws:connected" in reason
            for _, status, reason in segment
        )
        complete = (
            start_anchor_gap_ms is not None
            and start_anchor_gap_ms <= HEALTH_COVERAGE_MAX_GAP_MS
            and end_age_ms is not None
            and end_age_ms <= HEALTH_COVERAGE_MAX_GAP_MS
            and max_gap_ms is not None
            and max_gap_ms <= HEALTH_COVERAGE_MAX_GAP_MS
            and all_connected
        )
        return {
            "complete": bool(complete),
            "start_anchor_gap_ms": start_anchor_gap_ms,
            "end_age_ms": end_age_ms,
            "max_health_gap_ms": max_gap_ms,
            "max_allowed_health_gap_ms": HEALTH_COVERAGE_MAX_GAP_MS,
            "all_health_rows_ok_and_liq_ws_connected": bool(all_connected),
        }

    def _symbol_snapshot(
        self,
        symbol: str,
        as_of_ms: int,
        live_health: dict[str, Any] | None,
    ) -> dict[str, Any]:
        out = super()._symbol_snapshot(symbol, as_of_ms, live_health)
        state = self.symbols[symbol]

        coverage: dict[str, Any] = {
            "policy": "boundary-anchor freshness + liquidation websocket health coverage",
            "spot_return": {},
            "perpetual_return": {},
            "open_interest_change": {},
            "liquidation": {},
        }

        spot_returns: dict[str, float | None] = {}
        perp_returns: dict[str, float | None] = {}
        oi_changes: dict[str, float | None] = {}
        dislocation: dict[str, float | None] = {}

        for label, window_ms in WINDOWS_MS.items():
            spot_value, spot_cov = self._change_with_coverage(
                state.spot_price, as_of_ms, window_ms
            )
            perp_value, perp_cov = self._change_with_coverage(
                state.perp_price, as_of_ms, window_ms
            )
            oi_value, oi_cov = self._change_with_coverage(
                state.open_interest, as_of_ms, window_ms
            )
            spot_returns[label] = spot_value
            perp_returns[label] = perp_value
            oi_changes[label] = oi_value
            dislocation[label] = (
                None
                if spot_value is None or perp_value is None
                else perp_value - spot_value
            )
            coverage["spot_return"][label] = spot_cov
            coverage["perpetual_return"][label] = perp_cov
            coverage["open_interest_change"][label] = oi_cov

        out["returns_pct"]["spot"] = spot_returns
        out["returns_pct"]["perpetual"] = perp_returns
        out["returns_pct"]["perp_minus_spot_pp"] = dislocation
        out["open_interest_change_pct"] = oi_changes

        long_liq: dict[str, float | None] = {}
        short_liq: dict[str, float | None] = {}
        net_liq: dict[str, float | None] = {}
        for label, window_ms in WINDOWS_MS.items():
            liq_cov = self._liquidation_coverage(
                symbol, as_of_ms, window_ms, live_health
            )
            coverage["liquidation"][label] = liq_cov
            if liq_cov["complete"]:
                long_value = self._sum_window(
                    state.liq_long_notional, as_of_ms, window_ms
                )
                short_value = self._sum_window(
                    state.liq_short_notional, as_of_ms, window_ms
                )
                long_liq[label] = long_value
                short_liq[label] = short_value
                net_liq[label] = short_value - long_value
            else:
                long_liq[label] = None
                short_liq[label] = None
                net_liq[label] = None

        out["liquidation_notional_usdt_est"] = {
            "long": long_liq,
            "short": short_liq,
            "net_short_minus_long": net_liq,
        }
        out["coverage"] = coverage
        return out


class MarketStateServiceCoverageFixed(MarketStateService):
    """Candidate service writing a separate coverage-aware shared snapshot."""

    def __init__(
        self,
        data_dir: Path,
        *,
        snapshot_name: str = "market_state_v1_coveragefix.json",
        interval_seconds: float = 1.0,
    ) -> None:
        super().__init__(
            data_dir,
            snapshot_name=snapshot_name,
            interval_seconds=interval_seconds,
        )
        self.engine = MarketStateEngineCoverageFixed()


def build_coverage_snapshot_from_records(
    records: Iterable[dict[str, Any]],
    *,
    as_of_ms: int,
    generation_id: int = 1,
    live_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    engine = MarketStateEngineCoverageFixed()
    for rec in records:
        engine.ingest(rec, as_of_ms=as_of_ms)
    return engine.snapshot(
        as_of_ms=as_of_ms,
        generation_id=generation_id,
        live_health=live_health,
    )
