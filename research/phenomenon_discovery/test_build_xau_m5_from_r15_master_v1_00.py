#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import lzma
import struct
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import build_xau_m5_from_r15_master_v1_00 as m

REC = struct.Struct(">IIIIIf")


def _payload(path: Path, seconds: list[int], base_raw: int = 2000000) -> str:
    raw = bytearray()
    for i, sec in enumerate(seconds):
        o = base_raw + i * 10
        c = o + 5
        lo = o - 2
        hi = c + 3
        raw += REC.pack(sec, o, c, lo, hi, 1.0)
    path.write_bytes(lzma.compress(bytes(raw)))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_five_m1_to_one_m5() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.bi5"
        h = _payload(p, [0, 60, 120, 180, 240])
        bars = m.decode_day(date(2025, 1, 2), p, h, p.stat().st_size)
        out, dropped = m.aggregate_m5(bars)
        assert dropped == 0
        assert len(out) == 1
        epoch, o, hi, lo, c = out[0]
        assert epoch == int(datetime(2025, 1, 2, tzinfo=timezone.utc).timestamp())
        assert o == 2000.000
        assert lo == 1999.998
        assert hi == 2000.048
        assert c == 2000.045


def test_partial_bucket_is_dropped_not_filled() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.bi5"
        h = _payload(p, [0, 60, 180, 240])
        bars = m.decode_day(date(2025, 1, 2), p, h, p.stat().st_size)
        out, dropped = m.aggregate_m5(bars)
        assert out == []
        assert dropped == 1


def test_sha_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.bi5"
        _payload(p, [0, 60, 120, 180, 240])
        try:
            m.decode_day(date(2025, 1, 2), p, "0" * 64, p.stat().st_size)
        except RuntimeError as e:
            assert "SHA256 mismatch" in str(e)
        else:
            raise AssertionError("SHA mismatch did not fail")


def test_2026_hard_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = root / "x.bi5"
        h = _payload(p, [0, 60, 120, 180, 240])
        idx = root / "index.csv"
        with idx.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "path", "sha256", "bytes"])
            w.writeheader()
            w.writerow({"date": "2026-01-01", "path": str(p), "sha256": h, "bytes": p.stat().st_size})
        try:
            m.parse_index(idx)
        except RuntimeError as e:
            assert "PROTECTED 2026" in str(e)
        else:
            raise AssertionError("2026 source did not fail")


def test_output_contract_matches_r16_loader() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = root / "x.bi5"
        h = _payload(p, [0, 60, 120, 180, 240])
        idx = root / "index.csv"
        with idx.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "path", "sha256", "bytes"])
            w.writeheader()
            w.writerow({"date": "2025-01-02", "path": str(p), "sha256": h, "bytes": p.stat().st_size})
        out = root / "m5.csv"
        result = m.build(idx, out)
        assert result["status"] == "PASS"
        with out.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert list(rows[0].keys()) == ["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close"]
        assert rows[0]["symbol"] == "XAUUSD"
        assert rows[0]["timeframe"] == "M5"
        assert rows[0]["open"] == "2000.000"


if __name__ == "__main__":
    test_exact_five_m1_to_one_m5()
    test_partial_bucket_is_dropped_not_filled()
    test_sha_mismatch_fails()
    test_2026_hard_fails()
    test_output_contract_matches_r16_loader()
    print("PASS")
