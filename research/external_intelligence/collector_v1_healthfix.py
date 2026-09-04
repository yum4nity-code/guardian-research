#!/usr/bin/env python3
"""EIB V1 health-record spam hotfix prototype.

Keeps the live `health.json` snapshot at the normal fast cadence, but persists
health events only when the *semantic* health state changes or once per minute.
Dynamic age values in the human-readable reason no longer make every 5-second
snapshot look like a new event.

Research hotfix only. This subclasses collector_v1 so the validated collector
logic is otherwise untouched while the change is smoke-tested.
"""

from __future__ import annotations

import asyncio
from typing import Any

from collector_v1 import BYBIT_WS_LINEAR, CANONICAL_TO_BYBIT, BybitCollector, make_record, now_ms, utc_iso


def stable_health_signature(status: str, reason: str) -> tuple[str, str]:
    """Return a semantic signature with volatile age/error detail stripped.

    Examples:
    - spot:ok:2518ms -> spot:ok
    - perpetual:stale:30214ms -> perpetual:stale
    - spot:last_error:ClientConnectorError: ... -> spot:last_error
    - liq_ws:connected / liq_ws:down are already stable

    The full `reason` is still written to health.json and to the persisted
    event payload whenever a semantic transition/heartbeat is emitted.
    """
    stable_parts: list[str] = []
    for part in reason.split(";"):
        if ":ok:" in part:
            stable_parts.append(part.split(":ok:", 1)[0] + ":ok")
        elif ":stale:" in part:
            stable_parts.append(part.split(":stale:", 1)[0] + ":stale")
        elif ":last_error:" in part:
            stable_parts.append(part.split(":last_error:", 1)[0] + ":last_error")
        else:
            stable_parts.append(part)
    return status, ";".join(stable_parts)


class BybitCollectorHealthFixed(BybitCollector):
    """BybitCollector with health-event dedupe fixed; market collection unchanged."""

    async def health_loop(self) -> None:
        while not self.stop_event.is_set():
            now = now_ms()
            snapshot: dict[str, Any] = {
                "schema_version": 1,
                "collector": "guardian-eib-v1-bybit-healthfix",
                "updated_at_ms": now,
                "updated_at_utc": utc_iso(now),
                "started_at_ms": self.state.started_at_ms,
                "ws_connected": self.state.ws_connected,
                "symbols": {},
            }
            health_records: list[dict[str, Any]] = []
            for canonical in self.symbols:
                status, reason = self._metric_status(canonical, now)
                snapshot["symbols"][canonical] = {"status": status, "reason": reason}
                sig = stable_health_signature(status, reason)
                last_event = self._last_health_event_ms.get(canonical, 0)

                # Persist only semantic state transitions and one heartbeat/min.
                if self._last_health_signature.get(canonical) != sig or now - last_event >= 60_000:
                    rec = make_record(
                        canonical_symbol=canonical,
                        venue="BYBIT",
                        market_type="aggregate",
                        metric="health",
                        source_symbol=CANONICAL_TO_BYBIT[canonical],
                        source_ts_ms=now,
                        received_ts_ms=now,
                        value=status,
                        unit="status",
                        raw_ref="collector:health",
                        quality_reason=reason,
                        id_extra=reason,
                    )
                    rec["quality"]["status"] = status
                    rec["quality"]["age_ms"] = 0
                    rec["quality"]["reason"] = reason
                    health_records.append(rec)
                    self._last_health_signature[canonical] = sig
                    self._last_health_event_ms[canonical] = now

            if health_records:
                await self.recorder.write(health_records)
            await self.recorder.write_health_snapshot(snapshot)
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.health_seconds)
            except asyncio.TimeoutError:
                pass
