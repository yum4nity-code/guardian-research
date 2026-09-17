#!/usr/bin/env python3
"""Fail-closed, streaming data admission primitives for Edge Atlas.

This module performs no strategy calculation. It admits only the sources pinned in
ADMITTED_DATA_MANIFEST.json and never loads a complete history into memory.
"""
from __future__ import annotations

import csv
import hashlib
import lzma
import re
import struct
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator

UTC = timezone.utc
PROTECTED_START = datetime(2026, 1, 1, tzinfo=UTC)
BINANCE_COLUMNS = (
    "time", "open", "high", "low", "close", "volume", "quote_volume",
    "trades", "taker_buy_base", "taker_buy_quote",
)
FORBIDDEN_BINANCE_TOKENS = ("oi", "open_interest", "funding", "derivative", "perpetual")
YEAR_2026 = re.compile(r"(^|[^0-9])2026([^0-9]|$)")


class AdmissionError(RuntimeError):
    status = "BLOCKED_DATA"


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    available_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


@dataclass(frozen=True)
class CostProfile:
    name: str
    spread_bps: float
    slippage_bps: float
    commission_bps: float


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reject_2026_path(path: Path) -> None:
    if YEAR_2026.search(str(path)):
        raise AdmissionError(f"2026 path forbidden: {path}")


def require_hash(path: Path, expected: str) -> None:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected or ""):
        raise AdmissionError(f"missing/invalid pinned SHA-256 for {path}")
    actual = sha256(path)
    if actual.lower() != expected.lower():
        raise AdmissionError(f"SHA-256 mismatch for {path}: {actual}")


def parse_utc(value: str) -> datetime:
    raw = value.strip()
    if not (raw.endswith("Z") or raw.endswith("+00:00")):
        raise AdmissionError(f"timezone absent or non-UTC: {value!r}")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdmissionError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise AdmissionError(f"ambiguous/non-UTC timestamp: {value!r}")
    return parsed.astimezone(UTC)


def _float(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise AdmissionError(f"invalid numeric field {key}") from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise AdmissionError(f"non-finite numeric field {key}")
    return value


def iter_binance_spot_m5(
    path: Path,
    expected_sha256: str,
    start: datetime,
    end_exclusive: datetime,
) -> Iterator[Bar]:
    """Stream and validate one Binance spot file; any row at 2026+ blocks it."""
    reject_2026_path(path)
    require_hash(path, expected_sha256)
    if start.tzinfo != UTC or end_exclusive.tzinfo != UTC or not start < end_exclusive <= PROTECTED_START:
        raise AdmissionError("invalid/ambiguous Binance admission window")
    previous_all: datetime | None = None
    previous_admitted: datetime | None = None
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(reader.fieldnames or ())
        lowered = {field.strip().lower() for field in fields}
        if fields != BINANCE_COLUMNS:
            raise AdmissionError(f"unexpected Binance spot schema: {fields}")
        if any(token in lowered for token in FORBIDDEN_BINANCE_TOKENS):
            raise AdmissionError("OI/funding/derivative column forbidden")
        for row in reader:
            ts = parse_utc(row["time"])
            if ts >= PROTECTED_START:
                raise AdmissionError(f"2026 row forbidden: {row['time']}")
            if previous_all is not None and ts <= previous_all:
                raise AdmissionError("duplicate or non-monotone Binance timestamp")
            previous_all = ts
            if not start <= ts < end_exclusive:
                continue
            if ts.second or ts.microsecond or ts.minute % 5:
                raise AdmissionError(f"off-grid M5 timestamp: {ts.isoformat()}")
            if previous_admitted is not None and ts - previous_admitted != timedelta(minutes=5):
                raise AdmissionError("inconsistent M5 cadence in admitted window")
            previous_admitted = ts
            op, hi, lo, cl = (_float(row, key) for key in ("open", "high", "low", "close"))
            if min(op, hi, lo, cl) <= 0 or hi < max(op, cl) or lo > min(op, cl) or hi < lo:
                raise AdmissionError("invalid Binance OHLC")
            yield Bar(ts, ts + timedelta(minutes=5), op, hi, lo, cl, _float(row, "volume"))


def load_dukascopy_index(path: Path, expected_sha256: str) -> Iterator[dict[str, str]]:
    reject_2026_path(path)
    require_hash(path, expected_sha256)
    previous: date | None = None
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ("date", "path", "sha256", "bytes"):
            raise AdmissionError("unexpected Dukascopy index schema")
        for row in reader:
            try:
                day = date.fromisoformat(row["date"])
                size = int(row["bytes"])
            except (ValueError, TypeError) as exc:
                raise AdmissionError("invalid Dukascopy index metadata") from exc
            payload = Path(row["path"])
            if day.year >= 2026 or YEAR_2026.search(row["date"]) or YEAR_2026.search(str(payload)):
                raise AdmissionError("2026 Dukascopy payload forbidden")
            if "r30" in str(payload).lower() or payload.suffix.lower() != ".bi5":
                raise AdmissionError("artificial R30/non-BI5 source forbidden")
            if previous is not None and day <= previous:
                raise AdmissionError("duplicate or non-monotone Dukascopy index date")
            if previous is not None:
                expected = previous + timedelta(days=1)
                while expected.weekday() >= 5:
                    expected += timedelta(days=1)
                if day != expected:
                    raise AdmissionError(f"Dukascopy weekday coverage gap: {previous} -> {day}")
            if day.weekday() >= 5 or size <= 0 or not re.fullmatch(r"[0-9a-fA-F]{64}", row["sha256"]):
                raise AdmissionError("invalid Dukascopy provenance row")
            previous = day
            rows.append(row)
    yield from rows


def decode_dukascopy_m1_day(
    row: dict[str, str],
    expected_records: int | None = 1440,
) -> Iterator[Bar]:
    payload_path = Path(row["path"])
    reject_2026_path(payload_path)
    if "r30" in str(payload_path).lower() or payload_path.suffix.lower() != ".bi5":
        raise AdmissionError("R30/non-BI5 Dukascopy source forbidden")
    if not payload_path.is_file() or payload_path.stat().st_size != int(row["bytes"]):
        raise AdmissionError("missing/size-mismatched Dukascopy payload")
    require_hash(payload_path, row["sha256"])
    day = date.fromisoformat(row["date"])
    if day.year >= 2026:
        raise AdmissionError("2026 Dukascopy day forbidden")
    try:
        raw = lzma.decompress(payload_path.read_bytes())
    except lzma.LZMAError as exc:
        raise AdmissionError("invalid Dukascopy LZMA payload") from exc
    if not raw or len(raw) % 24:
        raise AdmissionError("invalid Dukascopy record layout")
    count = len(raw) // 24
    if expected_records is not None and count != expected_records:
        raise AdmissionError(f"unexpected M1 records/day: {count}")
    previous: datetime | None = None
    base = datetime(day.year, day.month, day.day, tzinfo=UTC)
    for offset in range(0, len(raw), 24):
        second, op, hi, lo, cl, volume = struct.unpack_from(">5If", raw, offset)
        if not 0 <= second < 86400 or min(op, hi, lo, cl) <= 0:
            raise AdmissionError("invalid Dukascopy candle record")
        ts = base + timedelta(seconds=second)
        if ts >= PROTECTED_START:
            raise AdmissionError("2026 Dukascopy timestamp forbidden")
        if previous is not None and ts - previous != timedelta(minutes=1):
            raise AdmissionError("duplicate/non-monotone/inconsistent M1 cadence")
        if ts.second or ts.microsecond:
            raise AdmissionError("off-grid Dukascopy M1 timestamp")
        previous = ts
        # Raw Dukascopy XAU integers use 1/1000 price precision.
        values = tuple(value / 1000.0 for value in (op, hi, lo, cl))
        if values[1] < max(values[0], values[3]) or values[2] > min(values[0], values[3]) or values[1] < values[2]:
            raise AdmissionError("invalid Dukascopy OHLC")
        yield Bar(ts, ts + timedelta(minutes=1), *values, float(volume))


def aggregate_m1_to_m5(bars: Iterable[Bar]) -> Iterator[Bar]:
    bucket: list[Bar] = []
    for bar in bars:
        if bar.timestamp.tzinfo != UTC or bar.available_at != bar.timestamp + timedelta(minutes=1):
            raise AdmissionError("non-causal/ambiguous M1 availability")
        if not bucket:
            if bar.timestamp.minute % 5:
                raise AdmissionError("M5 bucket does not start on boundary")
        elif bar.timestamp - bucket[-1].timestamp != timedelta(minutes=1):
            raise AdmissionError("M1 gap inside M5 bucket")
        bucket.append(bar)
        if len(bucket) == 5:
            start = bucket[0].timestamp
            yield Bar(
                timestamp=start,
                available_at=bucket[-1].available_at,
                open=bucket[0].open,
                high=max(item.high for item in bucket),
                low=min(item.low for item in bucket),
                close=bucket[-1].close,
                volume=sum(item.volume or 0.0 for item in bucket),
            )
            bucket = []
    if bucket:
        raise AdmissionError("incomplete trailing M5 bucket")


def require_available_before_decision(bar: Bar, decision_time: datetime) -> None:
    if decision_time.tzinfo != UTC or bar.available_at > decision_time:
        raise AdmissionError("data unavailable at decision time")


def first_open_at_or_after(bars: Iterable[Bar], signal_close: datetime) -> tuple[datetime, float]:
    if signal_close.tzinfo != UTC:
        raise AdmissionError("signal close timezone must be UTC")
    previous: datetime | None = None
    for bar in bars:
        if bar.timestamp.tzinfo != UTC or (previous is not None and bar.timestamp <= previous):
            raise AdmissionError("entry bars must be UTC, unique and monotone")
        previous = bar.timestamp
        if bar.timestamp >= signal_close:
            return bar.timestamp, bar.open
    raise AdmissionError("no entry open available after signal close")


def partition_for(timestamp: datetime, market: str) -> str:
    if timestamp.tzinfo != UTC or timestamp >= PROTECTED_START:
        raise AdmissionError("ambiguous/protected partition timestamp")
    year = timestamp.year
    if market == "XAU":
        if 2017 <= year <= 2022:
            return "discovery"
        if 2023 <= year <= 2024:
            return "confirmation"
        if year == 2025:
            return "pre_oos"
    elif market == "CRYPTO_SPOT":
        if year == 2024:
            return "discovery"
        if year == 2025:
            return "confirmation"
    raise AdmissionError(f"timestamp outside frozen {market} partitions")


def validate_cost_profiles(nominal: CostProfile, stress: CostProfile) -> None:
    if nominal.name != "nominal" or stress.name != "stress" or nominal is stress:
        raise AdmissionError("nominal/stress cost profiles must be distinct")
    for profile in (nominal, stress):
        if min(profile.spread_bps, profile.slippage_bps, profile.commission_bps) < 0:
            raise AdmissionError("negative cost forbidden")
    if not (
        stress.spread_bps >= nominal.spread_bps
        and stress.slippage_bps >= nominal.slippage_bps
        and stress.commission_bps >= nominal.commission_bps
        and stress != nominal
    ):
        raise AdmissionError("stress costs must be separately defined and no lower than nominal")
