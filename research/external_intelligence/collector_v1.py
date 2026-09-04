#!/usr/bin/env python3
"""Guardian External Intelligence Bus V1 collector (research only).

Collects public, read-only Bybit market data for BTC/ETH:
- spot last price
- USDT perpetual last price
- perpetual open interest
- perpetual funding rate
- all liquidation events (long/short)

Writes normalized JSONL records compatible with schema_v1.json plus an atomic
health.json snapshot. No API key is used. No trading endpoint is called.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import aiohttp

SCHEMA_VERSION = 1
BYBIT_REST = "https://api.bybit.com"
BYBIT_WS_LINEAR = "wss://stream.bybit.com/v5/public/linear"

CANONICAL_TO_BYBIT = {
    "BTCUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT",
}

STALE_AFTER_MS = {
    "last_price": 15_000,
    "open_interest": 60_000,
    "funding_rate": 300_000,
    "liquidation_notional": 5_000,
    "liquidation_qty": 5_000,
    "health": 30_000,
}


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def utc_iso(ts_ms: int | None = None) -> str:
    if ts_ms is None:
        ts_ms = now_ms()
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def canonical_for_source_symbol(source_symbol: str) -> str | None:
    source_symbol = source_symbol.upper()
    for canonical, bybit_symbol in CANONICAL_TO_BYBIT.items():
        if source_symbol == bybit_symbol:
            return canonical
    return None


def event_id_for(*parts: Any) -> str:
    payload = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def quality_for(source_ts_ms: int, received_ts_ms: int, metric: str, *, reason: str | None = None) -> dict[str, Any]:
    stale_after = STALE_AFTER_MS[metric]
    age = max(0, received_ts_ms - source_ts_ms)
    status = "OK" if age <= stale_after else "STALE"
    return {
        "status": status,
        "age_ms": age,
        "stale_after_ms": stale_after,
        "reason": reason,
    }


def make_record(
    *,
    canonical_symbol: str,
    venue: str,
    market_type: str,
    metric: str,
    source_symbol: str | None,
    source_ts_ms: int,
    received_ts_ms: int,
    value: float | str | None,
    unit: str,
    side: str | None = None,
    price: float | None = None,
    quantity: float | None = None,
    sequence: str | int | None = None,
    raw_ref: str | None = None,
    quality_reason: str | None = None,
    id_extra: Any = None,
) -> dict[str, Any]:
    available_at_ms = received_ts_ms
    rec = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id_for(
            venue,
            market_type,
            metric,
            canonical_symbol,
            source_symbol,
            source_ts_ms,
            value,
            side,
            sequence,
            id_extra,
        ),
        "canonical_symbol": canonical_symbol,
        "venue": venue,
        "market_type": market_type,
        "metric": metric,
        "side": side,
        "source_symbol": source_symbol,
        "source_ts_ms": int(source_ts_ms),
        "received_ts_ms": int(received_ts_ms),
        "available_at_ms": int(available_at_ms),
        "value": value,
        "unit": unit,
        "price": price,
        "quantity": quantity,
        "sequence": sequence,
        "quality": quality_for(int(source_ts_ms), int(received_ts_ms), metric, reason=quality_reason),
        "raw_ref": raw_ref,
    }
    return rec


def normalize_spot_ticker(payload: dict[str, Any], canonical_symbol: str, received_ts_ms: int) -> list[dict[str, Any]]:
    result = payload.get("result") or {}
    items = result.get("list") or []
    if not items:
        raise ValueError("Bybit spot ticker response has no result.list")
    item = items[0]
    source_symbol = str(item.get("symbol") or CANONICAL_TO_BYBIT[canonical_symbol])
    price = parse_float(item.get("lastPrice"))
    if price is None or price <= 0:
        raise ValueError("Bybit spot ticker has invalid lastPrice")
    source_ts = int(payload.get("time") or received_ts_ms)
    return [
        make_record(
            canonical_symbol=canonical_symbol,
            venue="BYBIT",
            market_type="spot",
            metric="last_price",
            source_symbol=source_symbol,
            source_ts_ms=source_ts,
            received_ts_ms=received_ts_ms,
            value=price,
            unit="USDT",
            price=price,
            raw_ref="bybit:v5/market/tickers?category=spot",
        )
    ]


def normalize_linear_ticker(payload: dict[str, Any], canonical_symbol: str, received_ts_ms: int) -> list[dict[str, Any]]:
    result = payload.get("result") or {}
    items = result.get("list") or []
    if not items:
        raise ValueError("Bybit linear ticker response has no result.list")
    item = items[0]
    source_symbol = str(item.get("symbol") or CANONICAL_TO_BYBIT[canonical_symbol])
    source_ts = int(payload.get("time") or received_ts_ms)
    records: list[dict[str, Any]] = []

    price = parse_float(item.get("lastPrice"))
    if price is not None and price > 0:
        records.append(
            make_record(
                canonical_symbol=canonical_symbol,
                venue="BYBIT",
                market_type="perpetual",
                metric="last_price",
                source_symbol=source_symbol,
                source_ts_ms=source_ts,
                received_ts_ms=received_ts_ms,
                value=price,
                unit="USDT",
                price=price,
                raw_ref="bybit:v5/market/tickers?category=linear",
            )
        )

    oi = parse_float(item.get("openInterest"))
    if oi is not None and oi >= 0:
        records.append(
            make_record(
                canonical_symbol=canonical_symbol,
                venue="BYBIT",
                market_type="perpetual",
                metric="open_interest",
                source_symbol=source_symbol,
                source_ts_ms=source_ts,
                received_ts_ms=received_ts_ms,
                value=oi,
                unit=canonical_symbol[:3],
                raw_ref="bybit:v5/market/tickers?category=linear",
            )
        )

    funding = parse_float(item.get("fundingRate"))
    if funding is not None:
        records.append(
            make_record(
                canonical_symbol=canonical_symbol,
                venue="BYBIT",
                market_type="perpetual",
                metric="funding_rate",
                source_symbol=source_symbol,
                source_ts_ms=source_ts,
                received_ts_ms=received_ts_ms,
                value=funding,
                unit="fraction",
                raw_ref="bybit:v5/market/tickers?category=linear",
            )
        )

    if not records:
        raise ValueError("Bybit linear ticker response has no usable price/OI/funding")
    return records


def normalize_liquidation_message(payload: dict[str, Any], received_ts_ms: int) -> list[dict[str, Any]]:
    data = payload.get("data") or []
    out: list[dict[str, Any]] = []
    for item in data:
        source_symbol = str(item.get("s") or "")
        canonical = canonical_for_source_symbol(source_symbol)
        if canonical is None:
            continue
        side_raw = str(item.get("S") or "")
        # Bybit semantics: S=Buy means a LONG position was liquidated;
        # S=Sell means a SHORT position was liquidated.
        if side_raw == "Buy":
            liq_side = "long"
        elif side_raw == "Sell":
            liq_side = "short"
        else:
            liq_side = None

        qty = parse_float(item.get("v"))
        bankruptcy_price = parse_float(item.get("p"))
        if qty is None or qty < 0 or bankruptcy_price is None or bankruptcy_price <= 0:
            continue
        source_ts = int(item.get("T") or payload.get("ts") or received_ts_ms)
        approx_notional = qty * bankruptcy_price
        raw_key = (source_symbol, source_ts, side_raw, item.get("v"), item.get("p"))

        out.append(
            make_record(
                canonical_symbol=canonical,
                venue="BYBIT",
                market_type="perpetual",
                metric="liquidation_qty",
                source_symbol=source_symbol,
                source_ts_ms=source_ts,
                received_ts_ms=received_ts_ms,
                value=qty,
                unit=canonical[:3],
                side=liq_side,
                price=bankruptcy_price,
                quantity=qty,
                raw_ref="bybit:ws:allLiquidation",
                id_extra=raw_key,
            )
        )
        out.append(
            make_record(
                canonical_symbol=canonical,
                venue="BYBIT",
                market_type="perpetual",
                metric="liquidation_notional",
                source_symbol=source_symbol,
                source_ts_ms=source_ts,
                received_ts_ms=received_ts_ms,
                value=approx_notional,
                unit="USDT_est_bankruptcy_price",
                side=liq_side,
                price=bankruptcy_price,
                quantity=qty,
                raw_ref="bybit:ws:allLiquidation",
                quality_reason="Notional estimated as size * bankruptcy price; not exchange-reported executed notional",
                id_extra=raw_key,
            )
        )
    return out


@dataclass
class ChannelState:
    last_valid_received_ms: int = 0
    last_source_ts_ms: int = 0
    last_error: str | None = None
    connected: bool = False


@dataclass
class RuntimeState:
    channels: dict[str, ChannelState] = field(default_factory=dict)
    ws_connected: bool = False
    ws_last_pong_ms: int = 0
    ws_last_message_ms: int = 0
    started_at_ms: int = field(default_factory=now_ms)

    def channel(self, key: str) -> ChannelState:
        if key not in self.channels:
            self.channels[key] = ChannelState()
        return self.channels[key]


class JsonlRecorder:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._seen: set[str] = set()
        self._seen_fifo: list[str] = []
        self._seen_limit = 50_000
        self._lock = asyncio.Lock()

    def _daily_path(self, ts_ms: int) -> Path:
        day = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y%m%d")
        return self.data_dir / f"bybit_eib_v1_{day}.jsonl"

    async def write(self, records: Iterable[dict[str, Any]]) -> int:
        written = 0
        async with self._lock:
            grouped: dict[Path, list[str]] = {}
            for rec in records:
                eid = rec["event_id"]
                if eid in self._seen:
                    continue
                self._seen.add(eid)
                self._seen_fifo.append(eid)
                if len(self._seen_fifo) > self._seen_limit:
                    old = self._seen_fifo.pop(0)
                    self._seen.discard(old)
                p = self._daily_path(int(rec["available_at_ms"]))
                grouped.setdefault(p, []).append(json.dumps(rec, separators=(",", ":"), ensure_ascii=False))
                written += 1
            for path, lines in grouped.items():
                with path.open("a", encoding="utf-8", newline="\n") as f:
                    for line in lines:
                        f.write(line + "\n")
                    f.flush()
                    os.fsync(f.fileno())
        return written

    async def write_health_snapshot(self, snapshot: dict[str, Any]) -> None:
        tmp = self.data_dir / "health.json.tmp"
        dst = self.data_dir / "health.json"
        payload = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
        async with self._lock:
            tmp.write_text(payload + "\n", encoding="utf-8")
            os.replace(tmp, dst)


class BybitCollector:
    def __init__(
        self,
        symbols: list[str],
        recorder: JsonlRecorder,
        poll_seconds: float = 5.0,
        health_seconds: float = 5.0,
    ):
        self.symbols = symbols
        self.recorder = recorder
        self.poll_seconds = max(1.0, poll_seconds)
        self.health_seconds = max(2.0, health_seconds)
        self.state = RuntimeState()
        self.stop_event = asyncio.Event()
        self._last_health_signature: dict[str, tuple[str, str]] = {}
        self._last_health_event_ms: dict[str, int] = {}

    async def _rest_get(self, session: aiohttp.ClientSession, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = BYBIT_REST + path
        timeout = aiohttp.ClientTimeout(total=8)
        async with session.get(url, params=params, timeout=timeout) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {text[:250]}")
            payload = json.loads(text)
            if int(payload.get("retCode", 0)) != 0:
                raise RuntimeError(f"Bybit retCode={payload.get('retCode')} retMsg={payload.get('retMsg')}")
            return payload

    async def _poll_symbol(self, session: aiohttp.ClientSession, canonical: str) -> None:
        source_symbol = CANONICAL_TO_BYBIT[canonical]
        for market_type, category, normalizer in (
            ("spot", "spot", normalize_spot_ticker),
            ("perpetual", "linear", normalize_linear_ticker),
        ):
            key = f"rest:{market_type}:{canonical}"
            st = self.state.channel(key)
            try:
                payload = await self._rest_get(
                    session,
                    "/v5/market/tickers",
                    {"category": category, "symbol": source_symbol},
                )
                received = now_ms()
                records = normalizer(payload, canonical, received)
                await self.recorder.write(records)
                st.last_valid_received_ms = received
                st.last_source_ts_ms = max(int(r["source_ts_ms"]) for r in records)
                st.last_error = None
                st.connected = True
            except Exception as exc:  # noqa: BLE001 - collector must stay alive
                st.last_error = f"{type(exc).__name__}: {exc}"
                st.connected = False

    async def rest_loop(self, session: aiohttp.ClientSession) -> None:
        while not self.stop_event.is_set():
            started = time.monotonic()
            await asyncio.gather(*(self._poll_symbol(session, s) for s in self.symbols))
            elapsed = time.monotonic() - started
            wait_for = max(0.1, self.poll_seconds - elapsed)
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=wait_for)
            except asyncio.TimeoutError:
                pass

    async def _ws_ping_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while not self.stop_event.is_set() and not ws.closed:
            await asyncio.sleep(20)
            if ws.closed:
                break
            try:
                await ws.send_json({"op": "ping"})
            except Exception:
                return

    async def ws_liquidation_loop(self, session: aiohttp.ClientSession) -> None:
        backoff = 1.0
        topics = [f"allLiquidation.{CANONICAL_TO_BYBIT[s]}" for s in self.symbols]
        while not self.stop_event.is_set():
            try:
                timeout = aiohttp.ClientWSTimeout(ws_receive=90, ws_close=10)
                async with session.ws_connect(BYBIT_WS_LINEAR, timeout=timeout, autoping=True, heartbeat=30) as ws:
                    self.state.ws_connected = True
                    self.state.ws_last_message_ms = now_ms()
                    await ws.send_json({"op": "subscribe", "args": topics})
                    ping_task = asyncio.create_task(self._ws_ping_loop(ws))
                    backoff = 1.0
                    try:
                        async for msg in ws:
                            received = now_ms()
                            self.state.ws_last_message_ms = received
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                payload = json.loads(msg.data)
                                if payload.get("op") == "pong" or payload.get("ret_msg") == "pong":
                                    self.state.ws_last_pong_ms = received
                                    continue
                                if str(payload.get("topic", "")).startswith("allLiquidation."):
                                    records = normalize_liquidation_message(payload, received)
                                    if records:
                                        await self.recorder.write(records)
                            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                                break
                    finally:
                        ping_task.cancel()
                        with contextlib_suppress(asyncio.CancelledError):
                            await ping_task
            except Exception as exc:  # noqa: BLE001
                for canonical in self.symbols:
                    st = self.state.channel(f"ws:liquidation:{canonical}")
                    st.last_error = f"{type(exc).__name__}: {exc}"
                    st.connected = False
                self.state.ws_connected = False
            finally:
                self.state.ws_connected = False

            if self.stop_event.is_set():
                break
            jitter = random.uniform(0, min(1.0, backoff / 4))
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=backoff + jitter)
            except asyncio.TimeoutError:
                pass
            backoff = min(30.0, backoff * 2)

    def _metric_status(self, canonical: str, now: int) -> tuple[str, str]:
        details: list[str] = []
        states: list[str] = []
        for market_type in ("spot", "perpetual"):
            st = self.state.channel(f"rest:{market_type}:{canonical}")
            if st.last_valid_received_ms <= 0:
                states.append("DOWN")
                details.append(f"{market_type}:never")
                continue
            age = now - st.last_valid_received_ms
            limit = 20_000 if market_type == "spot" else 60_000
            if age > limit:
                states.append("STALE")
                details.append(f"{market_type}:stale:{age}ms")
            elif st.last_error:
                states.append("PARTIAL")
                details.append(f"{market_type}:last_error:{st.last_error}")
            else:
                states.append("OK")
                details.append(f"{market_type}:ok:{age}ms")

        if self.state.ws_connected:
            states.append("OK")
            details.append("liq_ws:connected")
        else:
            states.append("PARTIAL")
            details.append("liq_ws:down")

        if all(s == "DOWN" for s in states[:-1]):
            overall = "DOWN"
        elif "STALE" in states:
            overall = "STALE"
        elif "DOWN" in states or "PARTIAL" in states:
            overall = "PARTIAL"
        else:
            overall = "OK"
        return overall, ";".join(details)

    async def health_loop(self) -> None:
        while not self.stop_event.is_set():
            now = now_ms()
            snapshot: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "collector": "guardian-eib-v1-bybit",
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
                sig = (status, reason)
                last_event = self._last_health_event_ms.get(canonical, 0)
                # Persist health on change and at least once per minute.
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

    async def run(self) -> None:
        headers = {"User-Agent": "Guardian-EIB-Research-V1/1.0"}
        connector = aiohttp.TCPConnector(limit=16, ttl_dns_cache=300)
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            tasks = [
                asyncio.create_task(self.rest_loop(session), name="rest_loop"),
                asyncio.create_task(self.ws_liquidation_loop(session), name="liquidation_ws"),
                asyncio.create_task(self.health_loop(), name="health_loop"),
            ]
            try:
                await self.stop_event.wait()
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)


class contextlib_suppress:
    """Tiny local replacement for contextlib.suppress to keep dependencies obvious."""

    def __init__(self, *exceptions: type[BaseException]):
        self.exceptions = exceptions

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> bool:
        return exc_type is not None and issubclass(exc_type, self.exceptions)


def default_data_dir() -> Path:
    env = os.getenv("GUARDIAN_EIB_DATA_DIR")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(r"D:\MT5_Backtests\Research\ExternalIntelligence")
    return Path("./guardian_eib_data")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian External Intelligence Bus V1 collector")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--symbols", nargs="+", default=["BTCUSD", "ETHUSD"], choices=sorted(CANONICAL_TO_BYBIT))
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    return p.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    recorder = JsonlRecorder(args.data_dir)
    collector = BybitCollector(args.symbols, recorder, args.poll_seconds, args.health_seconds)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, collector.stop_event.set)
        except NotImplementedError:
            pass
    print(f"Guardian EIB V1 starting | symbols={','.join(args.symbols)} | data={args.data_dir}")
    print("Research only. Public market data. No API key. No trading endpoints.")
    await collector.run()
    print("Guardian EIB V1 stopped cleanly")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
