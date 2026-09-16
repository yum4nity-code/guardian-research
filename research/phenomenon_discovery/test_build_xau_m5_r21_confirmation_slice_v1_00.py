#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from datetime import date
from pathlib import Path

import build_xau_m5_r21_confirmation_slice_v1_00 as s


def test_builder_opens_only_confirmation_payloads_and_heartbeats():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p_discovery = root / "2019-06-28.bi5"
        p_confirmation = root / "2019-07-01.bi5"
        p_2025 = root / "2025-01-02.bi5"
        p_discovery.write_bytes(b"DISCOVERY-MUST-NOT-OPEN")
        p_confirmation.write_bytes(b"CONFIRMATION")
        p_2025.write_bytes(b"2025-MUST-NOT-OPEN")

        idx = root / "index.csv"
        with idx.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["date", "path", "sha256", "bytes"],
            )
            w.writeheader()
            for d, p in (
                ("2019-06-28", p_discovery),
                ("2019-07-01", p_confirmation),
                ("2025-01-02", p_2025),
            ):
                w.writerow({
                    "date": d,
                    "path": str(p),
                    "sha256": "a" * 64,
                    "bytes": p.stat().st_size,
                })

        opened = []
        callbacks = []

        class M1:
            def __init__(self, epoch):
                self.epoch = epoch
                self.open = 1400.0
                self.high = 1401.0
                self.low = 1399.0
                self.close = 1400.5

        def fake_decode(d, p, h, n):
            opened.append((d, str(p)))
            assert d == date(2019, 7, 1)
            assert p == p_confirmation
            base = 1561939200
            return [M1(base + i * 60) for i in range(5)]

        def fake_agg(m1):
            return [(1561939200, 1400.0, 1401.0, 1399.0, 1400.5)], 0

        old = s._canonical_builder_api
        s._canonical_builder_api = lambda: (
            fake_decode,
            fake_agg,
            lambda p: "f" * 64,
        )
        try:
            result = s.build(
                idx,
                root / "m5.csv",
                progress_callback=lambda state: callbacks.append(dict(state)),
            )
        finally:
            s._canonical_builder_api = old

        assert opened == [(date(2019, 7, 1), str(p_confirmation))]
        assert callbacks[-1]["completed"] == 1
        assert callbacks[-1]["total"] == 1
        assert result["stage"] == "confirmation"
        assert result["first_opened_payload_date"] == "2019-07-01"
        assert result["last_opened_payload_date"] == "2019-07-01"
        assert result["confirmation_opened"] is True
        assert result["pre_oos_2025_opened"] is False
        assert result["protected_2026_opened"] is False


def test_explicit_non_confirmation_payload_gate():
    for d in (
        date(2019, 6, 30),
        date(2025, 1, 1),
    ):
        try:
            s._assert_confirmation_payload_date(d)
        except RuntimeError as exc:
            assert "refusing to open non-confirmation payload" in str(exc)
        else:
            raise AssertionError(f"non-confirmation payload accepted: {d}")


def test_2026_index_hard_fails_even_though_not_selected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = root / "x.bi5"
        p.write_bytes(b"x")
        idx = root / "index.csv"
        with idx.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["date", "path", "sha256", "bytes"],
            )
            w.writeheader()
            w.writerow({
                "date": "2019-07-01",
                "path": str(p),
                "sha256": "a" * 64,
                "bytes": 1,
            })
            w.writerow({
                "date": "2026-01-02",
                "path": str(p),
                "sha256": "a" * 64,
                "bytes": 1,
            })

        try:
            s.parse_confirmation_rows(idx)
        except RuntimeError as exc:
            assert "PROTECTED 2026" in str(exc)
        else:
            raise AssertionError("2026 index row did not hard fail")


def main():
    test_builder_opens_only_confirmation_payloads_and_heartbeats()
    test_explicit_non_confirmation_payload_gate()
    test_2026_index_hard_fails_even_though_not_selected()
    print("PASS: sealed R21 confirmation builder v1.00 tests")


if __name__ == "__main__":
    main()
