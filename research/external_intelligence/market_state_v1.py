#!/usr/bin/env python3
"""Guardian shared market-state engine V1.

Consumes Guardian EIB V1 observations and publishes a compact, strategy-neutral
snapshot for all local Guardian instances. It never emits BUY/SELL decisions.

Live invariant: only observations with available_at_ms <= computation time are
eligible. Historical callers can pass an explicit as_of_ms for deterministic
replay.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Iterable

SCHEMA_VERSION = 1
SYMBOLS = ("BTCUSD", "ETHUSD")
WINDOWS_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}
MAX_HISTORY_MS = WINDOWS_MS["1h"] + 120_000


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def utc_iso(ts_ms: int | None = None) -> str:
    if ts_ms is None:
        ts_ms = now_ms()
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_change(current: float | None, past: float | None) -> float | None:
    if current is None or past is None or past == 0:
        return None
    return (current / past - 1.0) * 100.0


@dataclass
class SymbolSeries:
    spot_price: Deque[tuple[int, float]] = field(default_factory=deque)
    perp_price: Deque[tuple[int, float]] = field(default_factory=deque)
    open_interest: Deque[tuple[int, float]] = field(default_factory=deque)
    funding_rate: Deque[tuple[int, float]] = field(default_factory=deque)
    liq_long_notional: Deque[tuple[int, float]] = field(default_factory=deque)
    liq_short_notional: Deque[tuple[int, float]] = field(default_factory=deque)
    last_health: tuple[int, str] | None = None
    latest_available_at_ms: int = 0


class MarketStateEngine:
    """Incremental feature engine over availability-gated EIB V1 records."""

    def __init__(self) -> None:
        self.symbols: dict[str, SymbolSeries] = {s: SymbolSeries() for s in SYMBOLS}
        self.ingested_records = 0

    @staticmethod
    def _append(series: Deque[tuple[int, float]], ts_ms: int, value: float) -> None:
        if series and ts_ms < series[-1][0]:
            rows = list(series)
            rows.append((ts_ms, value))
            rows.sort(key=lambda x: x[0])
            series.clear()
            series.extend(rows)
        else:
            series.append((ts_ms, value))

    def ingest(self, rec: dict[str, Any], *, as_of_ms: int | None = None) -> bool:
        symbol = str(rec.get("canonical_symbol") or "")
        if symbol not in self.symbols:
            return False
        try:
            available_at_ms = int(rec["available_at_ms"])
        except (KeyError, TypeError, ValueError):
            return False
        if as_of_ms is not None and available_at_ms > as_of_ms:
            return False

        metric = str(rec.get("metric") or "")
        market_type = str(rec.get("market_type") or "")
        value = rec.get("value")
        state = self.symbols[symbol]
        accepted = False

        if metric == "last_price":
            num = _to_float(value)
            if num is not None and num > 0:
                if market_type == "spot":
                    self._append(state.spot_price, available_at_ms, num)
                    accepted = True
                elif market_type == "perpetual":
                    self._append(state.perp_price, available_at_ms, num)
                    accepted = True
        elif metric == "open_interest" and market_type == "perpetual":
            num = _to_float(value)
            if num is not None and num >= 0:
                self._append(state.open_interest, available_at_ms, num)
                accepted = True
        elif metric == "funding_rate" and market_type == "perpetual":
            num = _to_float(value)
            if num is not None:
                self._append(state.funding_rate, available_at_ms, num)
                accepted = True
        elif metric == "liquidation_notional" and market_type == "perpetual":
            num = _to_float(value)
            side = rec.get("side")
            if num is not None and num >= 0:
                if side == "long":
                    self._append(state.liq_long_notional, available_at_ms, num)
                    accepted = True
                elif side == "short":
                    self._append(state.liq_short_notional, available_at_ms, num)
                    accepted = True
        elif metric == "health":
            status = str(value) if value is not None else ""
            if status in {"OK", "STALE", "PARTIAL", "DOWN"}:
                state.last_health = (available_at_ms, status)
                accepted = True

        if accepted:
            state.latest_available_at_ms = max(state.latest_available_at_ms, available_at_ms)
            self.ingested_records += 1
        return accepted

    def prune(self, as_of_ms: int) -> None:
        cutoff = as_of_ms - MAX_HISTORY_MS
        for state in self.symbols.values():
            for series in (
                state.spot_price,
                state.perp_price,
                state.open_interest,
                state.funding_rate,
                state.liq_long_notional,
                state.liq_short_notional,
            ):
                while len(series) > 1 and series[1][0] < cutoff:
                    series.popleft()

    @staticmethod
    def _latest_at_or_before(series: Deque[tuple[int, float]], ts_ms: int) -> tuple[int, float] | None:
        for row in reversed(series):
            if row[0] <= ts_ms:
                return row
        return None

    @classmethod
    def _change_for_window(cls, series: Deque[tuple[int, float]], as_of_ms: int, window_ms: int) -> float | None:
        current = cls._latest_at_or_before(series, as_of_ms)
        past = cls._latest_at_or_before(series, as_of_ms - window_ms)
        if current is None or past is None:
            return None
        return _pct_change(current[1], past[1])

    @staticmethod
    def _sum_window(series: Deque[tuple[int, float]], as_of_ms: int, window_ms: int) -> float:
        start = as_of_ms - window_ms
        return sum(v for ts, v in series if start < ts <= as_of_ms)

    def _symbol_snapshot(self, symbol: str, as_of_ms: int, live_health: dict[str, Any] | None) -> dict[str, Any]:
        state = self.symbols[symbol]
        spot = self._latest_at_or_before(state.spot_price, as_of_ms)
        perp = self._latest_at_or_before(state.perp_price, as_of_ms)
        oi = self._latest_at_or_before(state.open_interest, as_of_ms)
        funding = self._latest_at_or_before(state.funding_rate, as_of_ms)

        spot_value = spot[1] if spot else None
        perp_value = perp[1] if perp else None
        oi_value = oi[1] if oi else None
        funding_value = funding[1] if funding else None

        spot_returns = {label: self._change_for_window(state.spot_price, as_of_ms, window) for label, window in WINDOWS_MS.items()}
        perp_returns = {label: self._change_for_window(state.perp_price, as_of_ms, window) for label, window in WINDOWS_MS.items()}
        oi_changes = {label: self._change_for_window(state.open_interest, as_of_ms, window) for label, window in WINDOWS_MS.items()}
        long_liq = {label: self._sum_window(state.liq_long_notional, as_of_ms, window) for label, window in WINDOWS_MS.items()}
        short_liq = {label: self._sum_window(state.liq_short_notional, as_of_ms, window) for label, window in WINDOWS_MS.items()}

        basis_pct = None
        if spot_value and perp_value:
            basis_pct = (perp_value / spot_value - 1.0) * 100.0

        dislocation = {
            label: None if spot_returns[label] is None or perp_returns[label] is None else perp_returns[label] - spot_returns[label]
            for label in WINDOWS_MS
        }

        latest_core_ts = max([x[0] for x in (spot, perp, oi, funding) if x is not None], default=0)
        core_age_ms = as_of_ms - latest_core_ts if latest_core_ts else None

        persisted_health_status = state.last_health[1] if state.last_health else None
        live_status = None
        live_reason = None
        if live_health:
            sym = (live_health.get("symbols") or {}).get(symbol) or {}
            live_status = sym.get("status")
            live_reason = sym.get("reason")
        health_status = live_status or persisted_health_status or "DOWN"

        return {
            "quality": {
                "status": health_status,
                "reason": live_reason,
                "core_age_ms": core_age_ms,
                "latest_available_at_ms": state.latest_available_at_ms or None,
            },
            "raw": {
                "spot_last": spot_value,
                "perp_last": perp_value,
                "open_interest": oi_value,
                "funding_rate": funding_value,
                "basis_pct": basis_pct,
            },
            "returns_pct": {
                "spot": spot_returns,
                "perpetual": perp_returns,
                "perp_minus_spot_pp": dislocation,
            },
            "open_interest_change_pct": oi_changes,
            "liquidation_notional_usdt_est": {
                "long": long_liq,
                "short": short_liq,
                "net_short_minus_long": {label: short_liq[label] - long_liq[label] for label in WINDOWS_MS},
            },
        }

    def snapshot(self, *, as_of_ms: int | None = None, generation_id: int | None = None, live_health: dict[str, Any] | None = None) -> dict[str, Any]:
        if as_of_ms is None:
            as_of_ms = now_ms()
        self.prune(as_of_ms)

        health_updated_at_ms = None
        if live_health:
            try:
                health_updated_at_ms = int(live_health.get("updated_at_ms"))
            except (TypeError, ValueError):
                health_updated_at_ms = None

        return {
            "schema_version": SCHEMA_VERSION,
            "engine": "guardian-market-state-v1",
            "generation_id": int(generation_id if generation_id is not None else as_of_ms),
            "computed_at_ms": int(as_of_ms),
            "computed_at_utc": utc_iso(as_of_ms),
            "health_snapshot_age_ms": None if health_updated_at_ms is None else max(0, as_of_ms - health_updated_at_ms),
            "symbols": {symbol: self._symbol_snapshot(symbol, as_of_ms, live_health) for symbol in SYMBOLS},
        }


def build_snapshot_from_records(records: Iterable[dict[str, Any]], *, as_of_ms: int, generation_id: int = 1, live_health: dict[str, Any] | None = None) -> dict[str, Any]:
    engine = MarketStateEngine()
    for rec in records:
        engine.ingest(rec, as_of_ms=as_of_ms)
    return engine.snapshot(as_of_ms=as_of_ms, generation_id=generation_id, live_health=live_health)


def _utc_daily_paths(data_dir: Path, at_ms: int) -> list[Path]:
    dt = datetime.fromtimestamp(at_ms / 1000, tz=timezone.utc)
    return [data_dir / f"bybit_eib_v1_{day.strftime('%Y%m%d')}.jsonl" for day in (dt - timedelta(days=1), dt)]


class IncrementalFileReader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.partial = ""

    def read_new(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        if self.path.stat().st_size < self.offset:
            self.offset = 0
            self.partial = ""
        with self.path.open("r", encoding="utf-8") as f:
            f.seek(self.offset)
            chunk = f.read()
            self.offset = f.tell()
        if not chunk:
            return []
        text = self.partial + chunk
        lines = text.splitlines(keepends=True)
        self.partial = ""
        if lines and not lines[-1].endswith(("\n", "\r")):
            self.partial = lines.pop()
        out: list[dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out


def load_health_snapshot(data_dir: Path) -> dict[str, Any] | None:
    try:
        return json.loads((data_dir / "health.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


class MarketStateService:
    """Tail EIB daily JSONL and publish one atomic shared snapshot per PC."""

    def __init__(self, data_dir: Path, *, snapshot_name: str = "market_state_v1.json", interval_seconds: float = 1.0) -> None:
        self.data_dir = data_dir
        self.snapshot_path = data_dir / snapshot_name
        self.interval_seconds = max(0.25, interval_seconds)
        self.engine = MarketStateEngine()
        self.stop_event = asyncio.Event()
        self._readers: dict[Path, IncrementalFileReader] = {}
        self._last_generation = 0

    def _ensure_readers(self, at_ms: int) -> None:
        keep = set(_utc_daily_paths(self.data_dir, at_ms))
        for p in keep:
            self._readers.setdefault(p, IncrementalFileReader(p))
        for p in list(self._readers):
            if p not in keep:
                del self._readers[p]

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
        snapshot = self.engine.snapshot(as_of_ms=at_ms, generation_id=generation, live_health=load_health_snapshot(self.data_dir))
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


def default_data_dir() -> Path:
    env = os.getenv("GUARDIAN_EIB_DATA_DIR")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(r"D:\MT5_Backtests\Research\ExternalIntelligence")
    return Path("./guardian_eib_data")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian shared market-state V1")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--interval-seconds", type=float, default=1.0)
    p.add_argument("--once", action="store_true")
    return p.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    service = MarketStateService(args.data_dir, interval_seconds=args.interval_seconds)
    if args.once:
        print(json.dumps(service.publish_once(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"Guardian Market State V1 starting | data={args.data_dir}")
    print("Strategy-neutral shared facts only. No trading endpoints. No BUY/SELL output.")
    await service.run()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
