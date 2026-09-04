#!/usr/bin/env python3
"""Guardian EIB V1 Binance collector candidate (research only).

Public/read-only collection for BTCUSDT and ETHUSDT:
- spot last price
- USDⓈ-M perpetual last price
- USDⓈ-M open interest
- latest funding rate
- liquidation force-order stream

Records use the existing EIB V1 schema but are written to a separate
`binance_eib_v1_YYYYMMDD.jsonl` stream. The validated Bybit collector is not
modified. No API key and no trading endpoint are used.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import aiohttp

from collector_v1 import make_record, now_ms, parse_float

BINANCE_SPOT_REST = "https://api.binance.com"
BINANCE_FAPI_REST = "https://fapi.binance.com"
BINANCE_FAPI_WS = "wss://fstream.binance.com/public/stream"

CANONICAL_TO_BINANCE = {
    "BTCUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT",
}

CORE_STALE_MS = {
    "spot": 15_000,
    "perpetual": 15_000,
    "open_interest": 60_000,
    "funding": 300_000,
}

REPLACE_RETRY_ATTEMPTS = 25
REPLACE_RETRY_DELAY_SECONDS = 0.01


def canonical_for_binance(source_symbol: str) -> str | None:
    source_symbol = str(source_symbol or "").upper()
    for canonical, symbol in CANONICAL_TO_BINANCE.items():
        if source_symbol == symbol:
            return canonical
    return None


def _replace_with_retry(tmp: Path, dst: Path) -> None:
    for attempt in range(REPLACE_RETRY_ATTEMPTS):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if attempt + 1 >= REPLACE_RETRY_ATTEMPTS:
                raise
            time.sleep(REPLACE_RETRY_DELAY_SECONDS)


class BinanceJsonlRecorder:
    """Separate append-only recorder so Binance never contaminates Bybit files."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._seen: set[str] = set()
        self._seen_fifo: list[str] = []
        self._seen_limit = 50_000
        self._lock = asyncio.Lock()

    def _daily_path(self, ts_ms: int) -> Path:
        day = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y%m%d")
        return self.data_dir / f"binance_eib_v1_{day}.jsonl"

    async def write(self, records: Iterable[dict[str, Any]]) -> int:
        written = 0
        async with self._lock:
            grouped: dict[Path, list[str]] = {}
            for rec in records:
                eid = str(rec["event_id"])
                if eid in self._seen:
                    continue
                self._seen.add(eid)
                self._seen_fifo.append(eid)
                if len(self._seen_fifo) > self._seen_limit:
                    old = self._seen_fifo.pop(0)
                    self._seen.discard(old)
                path = self._daily_path(int(rec["available_at_ms"]))
                grouped.setdefault(path, []).append(
                    json.dumps(rec, separators=(",", ":"), ensure_ascii=False)
                )
                written += 1
            for path, lines in grouped.items():
                with path.open("a", encoding="utf-8", newline="\n") as f:
                    for line in lines:
                        f.write(line + "\n")
                    f.flush()
                    os.fsync(f.fileno())
        return written

    async def write_health_snapshot(self, snapshot: dict[str, Any]) -> None:
        tmp = self.data_dir / "binance_health.json.tmp"
        dst = self.data_dir / "binance_health.json"
        payload = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        async with self._lock:
            tmp.write_text(payload, encoding="utf-8")
            _replace_with_retry(tmp, dst)


@dataclass
class ChannelState:
    last_valid_received_ms: int = 0
    last_source_ts_ms: int = 0
    last_error: str | None = None
    connected: bool = False


@dataclass
class BinanceRuntimeState:
    channels: dict[str, ChannelState] = field(default_factory=dict)
    ws_connected: bool = False
    ws_last_message_ms: int = 0
    started_at_ms: int = field(default_factory=now_ms)

    def channel(self, key: str) -> ChannelState:
        if key not in self.channels:
            self.channels[key] = ChannelState()
        return self.channels[key]


def normalize_spot_price(payload: dict[str, Any], canonical: str, received_ms: int) -> list[dict[str, Any]]:
    price = parse_float(payload.get("price"))
    if price is None or price <= 0:
        raise ValueError("Binance spot ticker invalid price")
    source_symbol = str(payload.get("symbol") or CANONICAL_TO_BINANCE[canonical])
    # /api/v3/ticker/price has no exchange timestamp. Availability is therefore
    # the receive timestamp and the record explicitly documents that limitation.
    return [make_record(
        canonical_symbol=canonical,
        venue="BINANCE",
        market_type="spot",
        metric="last_price",
        source_symbol=source_symbol,
        source_ts_ms=received_ms,
        received_ts_ms=received_ms,
        value=price,
        unit="USDT",
        price=price,
        raw_ref="binance:/api/v3/ticker/price",
        quality_reason="Binance spot ticker/price has no server timestamp; source_ts_ms=received_ts_ms",
    )]


def normalize_perp_price(payload: dict[str, Any], canonical: str, received_ms: int) -> list[dict[str, Any]]:
    price = parse_float(payload.get("price"))
    if price is None or price <= 0:
        raise ValueError("Binance futures ticker invalid price")
    source_symbol = str(payload.get("symbol") or CANONICAL_TO_BINANCE[canonical])
    source_ts = int(payload.get("time") or received_ms)
    return [make_record(
        canonical_symbol=canonical,
        venue="BINANCE",
        market_type="perpetual",
        metric="last_price",
        source_symbol=source_symbol,
        source_ts_ms=source_ts,
        received_ts_ms=received_ms,
        value=price,
        unit="USDT",
        price=price,
        raw_ref="binance:/fapi/v2/ticker/price",
    )]


def normalize_open_interest(payload: dict[str, Any], canonical: str, received_ms: int) -> list[dict[str, Any]]:
    oi = parse_float(payload.get("openInterest"))
    if oi is None or oi < 0:
        raise ValueError("Binance open interest invalid")
    source_symbol = str(payload.get("symbol") or CANONICAL_TO_BINANCE[canonical])
    source_ts = int(payload.get("time") or received_ms)
    return [make_record(
        canonical_symbol=canonical,
        venue="BINANCE",
        market_type="perpetual",
        metric="open_interest",
        source_symbol=source_symbol,
        source_ts_ms=source_ts,
        received_ts_ms=received_ms,
        value=oi,
        unit=canonical[:3],
        raw_ref="binance:/fapi/v1/openInterest",
    )]


def normalize_funding(payload: dict[str, Any], canonical: str, received_ms: int) -> list[dict[str, Any]]:
    funding = parse_float(payload.get("lastFundingRate"))
    if funding is None:
        raise ValueError("Binance premiumIndex missing lastFundingRate")
    source_symbol = str(payload.get("symbol") or CANONICAL_TO_BINANCE[canonical])
    source_ts = int(payload.get("time") or received_ms)
    return [make_record(
        canonical_symbol=canonical,
        venue="BINANCE",
        market_type="perpetual",
        metric="funding_rate",
        source_symbol=source_symbol,
        source_ts_ms=source_ts,
        received_ts_ms=received_ms,
        value=funding,
        unit="fraction",
        raw_ref="binance:/fapi/v1/premiumIndex",
    )]


def normalize_force_order_message(payload: dict[str, Any], received_ms: int) -> list[dict[str, Any]]:
    """Normalize one USDⓈ-M force-order snapshot.

    Binance's public forceOrder stream exposes the liquidation *order side*.
    SELL closes a long position; BUY closes a short position. The stream is a
    snapshot feed (at most the latest force order per symbol in each 1000 ms
    window), so notional is labelled observed/sampled rather than exhaustive.
    """
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if str(data.get("e") or "") != "forceOrder":
        return []
    order = data.get("o") or {}
    source_symbol = str(order.get("s") or "")
    canonical = canonical_for_binance(source_symbol)
    if canonical is None:
        return []

    side_raw = str(order.get("S") or "").upper()
    if side_raw == "SELL":
        liq_side = "long"
    elif side_raw == "BUY":
        liq_side = "short"
    else:
        return []

    qty = parse_float(order.get("z"))
    if qty is None or qty <= 0:
        qty = parse_float(order.get("q"))
    price = parse_float(order.get("ap"))
    if price is None or price <= 0:
        price = parse_float(order.get("p"))
    if qty is None or qty <= 0 or price is None or price <= 0:
        return []

    source_ts = int(order.get("T") or data.get("E") or received_ms)
    notional = qty * price
    raw_key = (source_symbol, source_ts, side_raw, order.get("z"), order.get("q"), order.get("ap"), order.get("p"))
    reason = (
        "Observed liquidation snapshot: Binance forceOrder publishes at most the latest force order "
        "per symbol per 1000ms; not exhaustive liquidation volume"
    )
    return [
        make_record(
            canonical_symbol=canonical,
            venue="BINANCE",
            market_type="perpetual",
            metric="liquidation_qty",
            source_symbol=source_symbol,
            source_ts_ms=source_ts,
            received_ts_ms=received_ms,
            value=qty,
            unit=canonical[:3],
            side=liq_side,
            price=price,
            quantity=qty,
            raw_ref="binance:ws:forceOrder",
            quality_reason=reason,
            id_extra=raw_key,
        ),
        make_record(
            canonical_symbol=canonical,
            venue="BINANCE",
            market_type="perpetual",
            metric="liquidation_notional",
            source_symbol=source_symbol,
            source_ts_ms=source_ts,
            received_ts_ms=received_ms,
            value=notional,
            unit="USDT_observed_forceOrder_snapshot",
            side=liq_side,
            price=price,
            quantity=qty,
            raw_ref="binance:ws:forceOrder",
            quality_reason=reason,
            id_extra=raw_key,
        ),
    ]


class BinanceCollector:
    def __init__(
        self,
        symbols: list[str],
        recorder: BinanceJsonlRecorder,
        poll_seconds: float = 5.0,
        health_seconds: float = 5.0,
    ) -> None:
        self.symbols = symbols
        self.recorder = recorder
        self.poll_seconds = max(1.0, poll_seconds)
        self.health_seconds = max(2.0, health_seconds)
        self.state = BinanceRuntimeState()
        self.stop_event = asyncio.Event()
        self._last_health_signature: dict[str, tuple[str, str]] = {}
        self._last_health_event_ms: dict[str, int] = {}

    async def _get(self, session: aiohttp.ClientSession, base: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=8)
        async with session.get(base + path, params=params, timeout=timeout) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {text[:250]}")
            payload = json.loads(text)
            if isinstance(payload, dict) and "code" in payload and int(payload.get("code", 0)) < 0:
                raise RuntimeError(f"Binance code={payload.get('code')} msg={payload.get('msg')}")
            if not isinstance(payload, dict):
                raise ValueError("unexpected Binance REST payload")
            return payload

    async def _poll_endpoint(
        self,
        session: aiohttp.ClientSession,
        canonical: str,
        channel_name: str,
        base: str,
        path: str,
        normalizer,
    ) -> None:
        symbol = CANONICAL_TO_BINANCE[canonical]
        key = f"rest:{channel_name}:{canonical}"
        st = self.state.channel(key)
        try:
            payload = await self._get(session, base, path, {"symbol": symbol})
            received = now_ms()
            records = normalizer(payload, canonical, received)
            await self.recorder.write(records)
            st.last_valid_received_ms = received
            st.last_source_ts_ms = max(int(r["source_ts_ms"]) for r in records)
            st.last_error = None
            st.connected = True
        except Exception as exc:  # collector must survive provider/network faults
            st.last_error = f"{type(exc).__name__}: {exc}"
            st.connected = False

    async def _poll_symbol(self, session: aiohttp.ClientSession, canonical: str) -> None:
        await asyncio.gather(
            self._poll_endpoint(session, canonical, "spot", BINANCE_SPOT_REST, "/api/v3/ticker/price", normalize_spot_price),
            self._poll_endpoint(session, canonical, "perpetual", BINANCE_FAPI_REST, "/fapi/v2/ticker/price", normalize_perp_price),
            self._poll_endpoint(session, canonical, "open_interest", BINANCE_FAPI_REST, "/fapi/v1/openInterest", normalize_open_interest),
            self._poll_endpoint(session, canonical, "funding", BINANCE_FAPI_REST, "/fapi/v1/premiumIndex", normalize_funding),
        )

    async def rest_loop(self, session: aiohttp.ClientSession) -> None:
        while not self.stop_event.is_set():
            started = time.monotonic()
            await asyncio.gather(*(self._poll_symbol(session, s) for s in self.symbols))
            wait_for = max(0.1, self.poll_seconds - (time.monotonic() - started))
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=wait_for)
            except asyncio.TimeoutError:
                pass

    def _ws_url(self) -> str:
        streams = "/".join(f"{CANONICAL_TO_BINANCE[s].lower()}@forceOrder" for s in self.symbols)
        return f"{BINANCE_FAPI_WS}?streams={streams}"

    async def liquidation_ws_loop(self, session: aiohttp.ClientSession) -> None:
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                async with session.ws_connect(self._ws_url(), heartbeat=120, receive_timeout=240) as ws:
                    self.state.ws_connected = True
                    backoff = 1.0
                    async for msg in ws:
                        if self.stop_event.is_set():
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            received = now_ms()
                            payload = json.loads(msg.data)
                            self.state.ws_last_message_ms = received
                            records = normalize_force_order_message(payload, received)
                            if records:
                                await self.recorder.write(records)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
            except Exception:
                pass
            finally:
                self.state.ws_connected = False

            if self.stop_event.is_set():
                break
            delay = min(30.0, backoff) + random.uniform(0.0, 0.35)
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            backoff = min(30.0, backoff * 2.0)

    def _semantic_health(self, canonical: str, at_ms: int) -> tuple[str, str, dict[str, Any]]:
        parts: list[str] = []
        detail: dict[str, Any] = {}
        core_good = True
        any_core_seen = False
        for name in ("spot", "perpetual", "open_interest", "funding"):
            st = self.state.channel(f"rest:{name}:{canonical}")
            age = None if st.last_valid_received_ms <= 0 else max(0, at_ms - st.last_valid_received_ms)
            fresh = bool(st.connected and age is not None and age <= CORE_STALE_MS[name])
            any_core_seen = any_core_seen or st.last_valid_received_ms > 0
            core_good = core_good and fresh
            parts.append(f"{name}:{'ok' if fresh else ('stale' if st.last_valid_received_ms > 0 else 'down')}")
            detail[name] = {"age_ms": age, "connected": st.connected, "last_error": st.last_error}

        parts.append(f"liq_ws:{'connected' if self.state.ws_connected else 'down'}")
        detail["liq_ws"] = {
            "connected": self.state.ws_connected,
            "last_message_age_ms": None if self.state.ws_last_message_ms <= 0 else max(0, at_ms - self.state.ws_last_message_ms),
        }
        if not any_core_seen:
            status = "DOWN"
        elif not core_good:
            status = "STALE"
        elif not self.state.ws_connected:
            status = "PARTIAL"
        else:
            status = "OK"
        return status, ";".join(parts), detail

    async def health_loop(self) -> None:
        while not self.stop_event.is_set():
            at = now_ms()
            snapshot: dict[str, Any] = {
                "collector": "guardian-eib-v1-binance",
                "schema_version": 1,
                "started_at_ms": self.state.started_at_ms,
                "updated_at_ms": at,
                "updated_at_utc": datetime.fromtimestamp(at / 1000, tz=timezone.utc).isoformat(),
                "ws_connected": self.state.ws_connected,
                "symbols": {},
            }
            health_records: list[dict[str, Any]] = []
            for canonical in self.symbols:
                status, reason, detail = self._semantic_health(canonical, at)
                snapshot["symbols"][canonical] = {"status": status, "reason": reason, "channels": detail}
                sig = (status, reason)
                last_event = self._last_health_event_ms.get(canonical, 0)
                if self._last_health_signature.get(canonical) != sig or at - last_event >= 60_000:
                    health_records.append(make_record(
                        canonical_symbol=canonical,
                        venue="BINANCE",
                        market_type="aggregate",
                        metric="health",
                        source_symbol=CANONICAL_TO_BINANCE[canonical],
                        source_ts_ms=at,
                        received_ts_ms=at,
                        value=status,
                        unit="status",
                        raw_ref="binance:collector:health",
                        quality_reason=reason,
                    ))
                    self._last_health_signature[canonical] = sig
                    self._last_health_event_ms[canonical] = at
            if health_records:
                await self.recorder.write(health_records)
            await self.recorder.write_health_snapshot(snapshot)
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.health_seconds)
            except asyncio.TimeoutError:
                pass

    async def run(self) -> None:
        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10, sock_read=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [
                asyncio.create_task(self.rest_loop(session), name="binance_rest"),
                asyncio.create_task(self.liquidation_ws_loop(session), name="binance_liquidations"),
                asyncio.create_task(self.health_loop(), name="binance_health"),
            ]
            try:
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    exc = task.exception()
                    if exc is not None:
                        raise exc
            finally:
                self.stop_event.set()
                await asyncio.gather(*tasks, return_exceptions=True)


def default_data_dir() -> Path:
    env = os.getenv("GUARDIAN_EIB_DATA_DIR")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(r"D:\MT5_Backtests\Research\ExternalIntelligence")
    return Path("./guardian_eib_data")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian EIB V1 Binance collector candidate")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    return p.parse_args()


async def async_main(args: argparse.Namespace) -> int:
    recorder = BinanceJsonlRecorder(args.data_dir)
    collector = BinanceCollector(["BTCUSD", "ETHUSD"], recorder, args.poll_seconds, args.health_seconds)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, collector.stop_event.set)
        except NotImplementedError:
            pass
    print("Guardian EIB V1 Binance collector START")
    print(f"data={args.data_dir}")
    print("PUBLIC / READ ONLY / NO API KEY / NO TRADING ENDPOINT")
    await collector.run()
    print("Guardian EIB V1 Binance collector STOP")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
