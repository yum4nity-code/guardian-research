#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from datetime import date
from pathlib import Path

import build_xau_m5_discovery_slice_v1_01 as s


def test_builder_never_opens_2025_payload():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p2019 = root / "2019.bi5"
        p2025 = root / "2025.bi5"
        p2019.write_bytes(b"selected")
        p2025.write_bytes(b"MUST-NOT-BE-OPENED")
        idx = root / "index.csv"
        with idx.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "path", "sha256", "bytes"])
            w.writeheader()
            w.writerow({"date": "2019-06-28", "path": str(p2019), "sha256": "a" * 64, "bytes": p2019.stat().st_size})
            w.writerow({"date": "2025-01-02", "path": str(p2025), "sha256": "b" * 64, "bytes": p2025.stat().st_size})

        opened = []

        class M1:
            def __init__(self, e):
                self.epoch = e
                self.open = 2000.0
                self.high = 2001.0
                self.low = 1999.0
                self.close = 2000.5

        def fake_decode(d, p, h, n):
            opened.append((d, str(p)))
            assert d == date(2019, 6, 28)
            assert p == p2019
            return [M1(1561680000 + i * 60) for i in range(5)]

        def fake_agg(m1):
            return [(1561680000, 2000.0, 2001.0, 1999.0, 2000.5)], 0

        def fake_sha(p):
            return "f" * 64

        old = s._canonical_builder_api
        s._canonical_builder_api = lambda: (fake_decode, fake_agg, fake_sha)
        try:
            out = root / "m5.csv"
            result = s.build(idx, out)
        finally:
            s._canonical_builder_api = old

        assert opened == [(date(2019, 6, 28), str(p2019))]
        assert result["last_opened_payload_date"] == "2019-06-28"
        assert result["pre_oos_2025_opened"] is False


def test_explicit_non_discovery_payload_gate():
    for d in (date(2019, 7, 1), date(2025, 1, 1)):
        try:
            s._assert_discovery_payload_date(d)
        except RuntimeError as e:
            assert "refusing to open non-discovery payload" in str(e)
        else:
            raise AssertionError(f"non-discovery payload date accepted: {d}")


def test_2026_index_hard_fails():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = root / "x.bi5"
        p.write_bytes(b"x")
        idx = root / "index.csv"
        with idx.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "path", "sha256", "bytes"])
            w.writeheader()
            w.writerow({"date": "2019-06-28", "path": str(p), "sha256": "a" * 64, "bytes": 1})
            w.writerow({"date": "2026-01-02", "path": str(p), "sha256": "a" * 64, "bytes": 1})
        try:
            s.parse_discovery_rows(idx)
        except RuntimeError as e:
            assert "PROTECTED 2026" in str(e)
        else:
            raise AssertionError("2026 index row did not fail")


def main():
    test_builder_never_opens_2025_payload()
    test_explicit_non_discovery_payload_gate()
    test_2026_index_hard_fails()
    print("PASS: discovery-only M5 builder v1.01 tests")


if __name__ == "__main__":
    main()
