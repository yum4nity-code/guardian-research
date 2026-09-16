#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import lzma
import math
import struct
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import xau_edge_discovery_r21_r25_v1_02 as m


def B(dt, o=100.0, h=101.0, l=99.0, c=100.0):
    return m.Bar(int(dt.timestamp()), dt, "M5", o, h, l, c)


def test_absolute_m5_grid_rejects_30_second_offset():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.csv"
        dt = datetime(2019, 1, 15, 13, 20, 30, tzinfo=timezone.utc)
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["timeframe", "server_epoch", "open", "high", "low", "close"])
            w.writeheader()
            w.writerow({"timeframe": "M5", "server_epoch": int(dt.timestamp()), "open": 100, "high": 101, "low": 99, "close": 100})
        try:
            m.load_generated_discovery_bars(p)
        except RuntimeError as e:
            assert "off-grid M5 timestamp" in str(e)
        else:
            raise AssertionError("08:20:30-equivalent off-grid bar was accepted")


def test_jackknife_fails_closed_if_required_replication_undefined():
    bars = []
    # Three baseline days at same clock. Only day 1 has a compressed event.
    for d, ret in [(1, 0.01), (2, 0.02), (3, 0.20)]:
        t = datetime(2019, 1, d, 12, 0, tzinfo=timezone.utc)
        bars.append(B(t, c=100.0))
        bars.append(B(t + timedelta(minutes=5), o=100.0, h=130.0, l=90.0, c=100.0 * (1 + ret)))
    events = [{
        "compression_state": "bottom10",
        "cluster_day": "2019-01-01",
        "utc_minute": 720,
        "abs_fwd_1b": 0.01,
    }]
    s = m.r22_complete_estimator_day_jackknife(bars, events, "bottom10", 1)
    assert s["mean"] is not None
    assert s["cluster_se"] is None
    assert s["cluster_t"] is None
    assert s["event_days"] == 1
    assert s["baseline_days"] == 3
    assert s["required_replicates"] == 3
    assert s["valid_replicates"] == 2
    assert s["undefined_delete_days"] == ["2019-01-01"]
    assert "undefined" in s["reason"]


def test_jackknife_regular_case_still_has_variance():
    bars = []
    for d, ret in [(1, 0.01), (2, 0.02), (3, 0.20)]:
        t = datetime(2019, 1, d, 12, 0, tzinfo=timezone.utc)
        bars.append(B(t, c=100.0))
        bars.append(B(t + timedelta(minutes=5), o=100.0, h=130.0, l=90.0, c=100.0 * (1 + ret)))
    events = [
        {"compression_state": "bottom10", "cluster_day": "2019-01-01", "utc_minute": 720, "abs_fwd_1b": 0.01},
        {"compression_state": "bottom10", "cluster_day": "2019-01-02", "utc_minute": 720, "abs_fwd_1b": 0.02},
    ]
    s = m.r22_complete_estimator_day_jackknife(bars, events, "bottom10", 1)
    assert s["undefined_delete_days"] == []
    assert s["required_replicates"] == 3
    assert s["valid_replicates"] == 3
    assert s["cluster_se"] is not None and s["cluster_se"] > 0
    assert s["cluster_t"] is not None
    loo = [0.02 - (0.02 + 0.20) / 2, 0.01 - (0.01 + 0.20) / 2, 0.0]
    expected_se = math.sqrt((2 / 3) * sum((x - sum(loo) / 3) ** 2 for x in loo))
    assert math.isclose(s["cluster_se"], expected_se, rel_tol=1e-12)


def test_jackknife_no_valid_events_preserves_baseline_coverage():
    bars = []
    for d in (1, 2, 3):
        t = datetime(2019, 1, d, 12, tzinfo=timezone.utc)
        bars.extend([B(t), B(t + timedelta(minutes=5), c=100.5)])
    # Event exists but this horizon has no usable label. Exercise the real summary.
    events = [{"compression_state": "bottom10", "cluster_day": "2019-01-01",
               "year": 2019, "utc_minute": 720, "abs_fwd_1b": None, "excess_abs_1b": None}]
    s = m.summarize("R22", events, bars)["states"]["bottom10"]["metrics"]["excess_abs_1b"]["clustered"]
    assert s["baseline_days"] == 3 and s["event_days"] == 0
    assert s["required_replicates"] == 3 and s["valid_replicates"] == 0
    assert s["undefined_delete_days"] == ["2019-01-01", "2019-01-02", "2019-01-03"]
    assert s["mean"] is None and s["cluster_se"] is None and s["cluster_t"] is None
    empty = m.r22_complete_estimator_day_jackknife([], [], "bottom10", 1)
    assert empty["baseline_days"] == empty["required_replicates"] == 0
    assert empty["undefined_delete_days"] == []


def _r24_day(breakout_open_minute: int | None):
    # Jan 15 2019: New York is UTC-5, so 08:20 NY = 13:20 UTC.
    start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
    bars = []
    for offset in range(0, 101, 5):  # through 10:00 NY inclusive
        dt = start + timedelta(minutes=offset)
        ny_minute = 8 * 60 + 20 + offset
        if offset < 15:
            o, h, l, c = 100, 101, 99, 100
        elif breakout_open_minute is not None and ny_minute == breakout_open_minute:
            o, h, l, c = 100, 103, 99, 102
        else:
            o, h, l, c = 100, 100.8, 99.2, 100
        bars.append(B(dt, o, h, l, c))
    return bars


def test_r24_accepts_0955_breakout():
    ev = m.r24_comex_opening_range_breakout(_r24_day(9 * 60 + 55))
    assert len(ev) == 1
    assert datetime.fromtimestamp(ev[0]["epoch"], tz=timezone.utc).astimezone(m.base.NEW_YORK_TZ).strftime("%H:%M") == "09:55"


def test_r24_excludes_1000_open_bar():
    ev = m.r24_comex_opening_range_breakout(_r24_day(10 * 60))
    assert ev == []


def test_r24_missing_bar_before_breakout_invalidates_day():
    bars = _r24_day(9 * 60 + 55)
    del bars[4]
    assert m.r24_comex_opening_range_breakout(bars) == []


def test_untrusted_index_paths_rejected_before_any_open_or_builder():
    alternatives = [
        Path("D:/untrusted/market_2019H2.csv"),
        Path("D:/untrusted/market_2025.csv"),
        Path("D:/untrusted/market_2026.csv"),
        Path("D:/untrusted") / m.CANONICAL_R15_INDEX.name,
    ]
    with patch.object(Path, "open", side_effect=AssertionError("unexpected file open")) as opened, \
         patch.object(m.sealed_builder, "build") as builder, \
         patch.object(m.tempfile, "TemporaryDirectory") as temporary:
        for path in alternatives:
            try:
                m.run_from_index(path, ["R21"])
            except RuntimeError as e:
                assert "non-canonical R15 index" in str(e)
            else:
                raise AssertionError(f"untrusted index accepted: {path}")
        with patch.object(sys, "argv", ["engine", "--index", str(alternatives[1]),
                                        "--output", "synthetic_never_written.json"]):
            try:
                m.main()
            except RuntimeError as e:
                assert "non-canonical R15 index" in str(e)
            else:
                raise AssertionError("CLI accepted arbitrary CSV as --index")
        opened.assert_not_called()
        builder.assert_not_called()
        temporary.assert_not_called()


def test_redirected_canonical_path_rejected_before_open():
    # Model a symlink/junction without requiring OS link privileges or market files.
    with patch.object(Path, "resolve", return_value=Path("D:/untrusted/market_2025.csv")), \
         patch.object(Path, "open", side_effect=AssertionError("unexpected file open")) as opened:
        try:
            m._read_canonical_r15_index(m.CANONICAL_R15_INDEX)
        except RuntimeError as e:
            assert "redirected canonical" in str(e)
        else:
            raise AssertionError("redirected canonical path accepted")
        opened.assert_not_called()


def test_index_digest_mismatch_blocks_builder():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "index.csv"
        p.write_bytes(b"synthetic modified metadata")
        with patch.object(m, "CANONICAL_R15_INDEX", p), \
             patch.object(m, "CANONICAL_R15_INDEX_SHA256", "0" * 64), \
             patch.object(m.sealed_builder, "build") as builder:
            try:
                m.run_from_index(p, ["R21"])
            except RuntimeError as e:
                assert "SHA256 mismatch" in str(e)
            else:
                raise AssertionError("modified index accepted")
            builder.assert_not_called()


def test_output_cannot_overwrite_trusted_index():
    with patch.object(sys, "argv", ["engine", "--index", str(m.CANONICAL_R15_INDEX),
                                    "--output", str(m.CANONICAL_R15_INDEX)]), \
         patch.object(m, "run_from_index") as run:
        try:
            m.main()
        except RuntimeError as e:
            assert "overwrite the canonical" in str(e)
        else:
            raise AssertionError("canonical index allowed as output")
        run.assert_not_called()


def test_builder_receipt_must_match_frozen_discovery_contract():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "generated.csv"
        p.write_text("x", encoding="utf-8")
        good = {
            "status": "PASS",
            "stage": "discovery",
            "stage_start": m.DISCOVERY_START.isoformat(),
            "stage_end_inclusive": m.DISCOVERY_END.isoformat(),
            "confirmation_opened": False,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            "output": str(p.resolve()),
            "last_opened_payload_date": "2019-06-28",
        }
        m._validate_builder_receipt(good, p)
        bad = dict(good)
        bad["pre_oos_2025_opened"] = True
        try:
            m._validate_builder_receipt(bad, p)
        except RuntimeError as e:
            assert "receipt mismatch" in str(e)
        else:
            raise AssertionError("unsafe builder receipt accepted")


def test_run_from_index_uses_internal_temp_builder_output_not_external_csv():
    with tempfile.TemporaryDirectory() as td:
        index = Path(td) / "master_index.csv"
        index.write_text("metadata only", encoding="utf-8")
        seen = {}
        old_build = m.sealed_builder.build

        def fake_build(index_path: Path, generated_csv: Path):
            seen["index"] = index_path
            seen["generated"] = generated_csv
            # A later replacement of the source cannot change the verified snapshot.
            index.write_text("changed after admission", encoding="utf-8")
            assert index_path.read_bytes() == b"metadata only"
            # Minimal aligned discovery bars around 08:20 NY.
            start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
            with generated_csv.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close"])
                w.writeheader()
                for i, price in enumerate([100, 101, 102, 103]):
                    dt = start + timedelta(minutes=5 * i)
                    w.writerow({
                        "symbol": "XAUUSD", "timeframe": "M5", "server_time": dt.isoformat(),
                        "server_epoch": int(dt.timestamp()), "open": price, "high": price + .1,
                        "low": price - .1, "close": price,
                    })
            return {
                "status": "PASS", "stage": "discovery",
                "stage_start": m.DISCOVERY_START.isoformat(),
                "stage_end_inclusive": m.DISCOVERY_END.isoformat(),
                "confirmation_opened": False, "pre_oos_2025_opened": False,
                "protected_2026_opened": False,
                "output": str(generated_csv.resolve()),
                "last_opened_payload_date": "2019-01-15",
            }

        m.sealed_builder.build = fake_build
        try:
            with patch.object(m, "CANONICAL_R15_INDEX", index), \
                 patch.object(m, "CANONICAL_R15_INDEX_SHA256", hashlib.sha256(b"metadata only").hexdigest()):
                payload = m.run_from_index(index, ["R21"])
        finally:
            m.sealed_builder.build = old_build

        assert seen["index"].name == "verified_r15_index.csv"
        assert seen["index"].parent == seen["generated"].parent
        assert seen["generated"].name == "sealed_discovery_m5.csv"
        assert seen["generated"].parent != index.parent
        assert payload["stage"] == "discovery"
        assert payload["confirmation_opened"] is False
        assert payload["pre_oos_2025_opened"] is False
        assert payload["protected_2026_opened"] is False
        assert payload["results"]["R21"]["summary"]["event_count"] == 1
        assert payload["source_index_sha256"] == hashlib.sha256(b"metadata only").hexdigest()


def test_pinned_index_real_builder_synthetic_integration():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        payload = root / "synthetic2019.bi5"
        record = struct.Struct(">IIIIIf")
        raw = b"".join(record.pack(13 * 3600 + 20 * 60 + 60 * i,
                                  100000, 100000 + i * 10, 99000, 102000, 1.0)
                       for i in range(20))
        payload.write_bytes(lzma.compress(raw))
        index = root / "index.csv"
        with index.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "path", "sha256", "bytes"])
            w.writerow(["2019-01-15", str(payload), hashlib.sha256(payload.read_bytes()).hexdigest(),
                        payload.stat().st_size])
            for day in ("2019-07-01", "2025-01-01"):
                w.writerow([day, str(root / f"forbidden_{day}.bi5"), "0" * 64, 1])
        digest = hashlib.sha256(index.read_bytes()).hexdigest()
        original_open = Path.open
        opened = []

        def observe(path, *args, **kwargs):
            opened.append(str(path))
            assert "forbidden_" not in str(path)
            return original_open(path, *args, **kwargs)

        with patch.object(m, "CANONICAL_R15_INDEX", index), \
             patch.object(m, "CANONICAL_R15_INDEX_SHA256", digest), \
             patch.object(Path, "open", observe):
            result = m.run_from_index(index, ["R21"])
        assert result["rows"] == 4
        assert result["builder_receipt"]["last_opened_payload_date"] == "2019-01-15"
        assert result["results"]["R21"]["summary"]["event_count"] == 1
        assert sum(path == str(index) for path in opened) == 1
        assert not Path(result["builder_receipt"]["output"]).exists()


def main():
    test_absolute_m5_grid_rejects_30_second_offset()
    test_jackknife_fails_closed_if_required_replication_undefined()
    test_jackknife_regular_case_still_has_variance()
    test_jackknife_no_valid_events_preserves_baseline_coverage()
    test_r24_accepts_0955_breakout()
    test_r24_excludes_1000_open_bar()
    test_r24_missing_bar_before_breakout_invalidates_day()
    test_untrusted_index_paths_rejected_before_any_open_or_builder()
    test_redirected_canonical_path_rejected_before_open()
    test_index_digest_mismatch_blocks_builder()
    test_output_cannot_overwrite_trusted_index()
    test_builder_receipt_must_match_frozen_discovery_contract()
    test_run_from_index_uses_internal_temp_builder_output_not_external_csv()
    test_pinned_index_real_builder_synthetic_integration()
    print("PASS: R21-R25 v1.02 second-audit regression tests")


if __name__ == "__main__":
    main()
