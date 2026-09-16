#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import xau_edge_discovery_r21_r25_v1_03 as discovery
import xau_r21_confirmation_v1_00 as stage
import xau_r26_confirmation_v1_00 as m


def test_reuses_exact_frozen_components():
    assert m.r26_event_extractor is discovery.r24_comex_opening_range_breakout
    assert m.sealed_builder is stage.sealed_builder


def _summary(r2_mean, r2_t, r4_mean, r4_t):
    return {
        "metrics": {
            "reversal_2b": {
                "clustered": {
                    "mean": r2_mean,
                    "cluster_t": r2_t,
                }
            },
            "reversal_4b": {
                "clustered": {
                    "mean": r4_mean,
                    "cluster_t": r4_t,
                }
            },
        }
    }


def test_joint_confirmation_gate_is_strict_and_fail_closed():
    assert m._confirmation_gate(
        _summary(0.0001, 2.01, 0.0002, 2.50)
    )["status"] == "PASS"

    cases = (
        _summary(0.0, 5.0, 0.0002, 2.50),
        _summary(0.0001, 2.0, 0.0002, 2.50),
        _summary(0.0001, 2.01, 0.0, 5.0),
        _summary(0.0001, 2.01, 0.0002, 2.0),
        _summary(None, None, 0.0002, 3.0),
    )
    for case in cases:
        assert m._confirmation_gate(case)["status"] == "FAIL"


def _write_confirmation_fixture(path: Path):
    rows = []

    # 2019-07-01: upward breakout at 08:35 NY, then reversal lower.
    start = datetime(2019, 7, 1, 12, 20, tzinfo=timezone.utc)
    closes = [100.0, 100.0, 100.0, 101.0, 100.8, 100.6, 100.4, 100.2]
    for i, close in enumerate(closes):
        if i < 3:
            high, low = 100.2, 99.8
        elif i == 3:
            high, low = 101.1, 100.9
        else:
            high, low = close + 0.1, close - 0.1
        rows.append((start + timedelta(minutes=5 * i), close, high, low))

    # 2024-12-31: downward breakout at 08:35 NY, then reversal higher.
    start = datetime(2024, 12, 31, 13, 20, tzinfo=timezone.utc)
    closes = [100.0, 100.0, 100.0, 99.0, 99.2, 99.4, 99.6, 99.8]
    for i, close in enumerate(closes):
        if i < 3:
            high, low = 100.2, 99.8
        elif i == 3:
            high, low = 99.1, 98.9
        else:
            high, low = close + 0.1, close - 0.1
        rows.append((start + timedelta(minutes=5 * i), close, high, low))

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "symbol",
                "timeframe",
                "server_time",
                "server_epoch",
                "open",
                "high",
                "low",
                "close",
            ],
        )
        w.writeheader()
        for dt, close, high, low in rows:
            w.writerow({
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "server_time": dt.isoformat(),
                "server_epoch": int(dt.timestamp()),
                "open": close,
                "high": high,
                "low": low,
                "close": close,
            })


def test_frozen_r24_event_definition_yields_positive_reversal_both_directions():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "fixture.csv"
        _write_confirmation_fixture(p)
        bars = stage.load_generated_confirmation_bars(p)
        events = m.r26_event_extractor(bars)

        assert len(events) == 2
        assert [e["direction"] for e in events] == [1, -1]

        for e in events:
            assert e["reversal_2b"] > 0
            assert e["reversal_4b"] > 0
            assert e["continuation_2b"] < 0
            assert e["continuation_4b"] < 0


def test_run_pipeline_is_r26_only_and_keeps_2025_2026_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        index = root / "master_index.csv"
        index.write_bytes(b"verified pinned index bytes")

        outdir = root / "r26_xau_confirmation_v100"
        output = outdir / "confirmation.json"
        progress = outdir / "progress.json"

        def fake_build(index_path: Path, generated_csv: Path, progress_callback=None):
            assert index_path.read_bytes() == b"verified pinned index bytes"
            _write_confirmation_fixture(generated_csv)

            if progress_callback:
                progress_callback({
                    "completed": 1,
                    "total": 2,
                    "last_opened_payload_date": "2019-07-01",
                    "decoded_m1": 100,
                    "emitted_m5": 8,
                })
                progress_callback({
                    "completed": 2,
                    "total": 2,
                    "last_opened_payload_date": "2024-12-31",
                    "decoded_m1": 200,
                    "emitted_m5": 16,
                })

            return {
                "status": "PASS",
                "stage": "confirmation",
                "stage_start": stage.CONFIRMATION_START.isoformat(),
                "stage_end_inclusive": stage.CONFIRMATION_END.isoformat(),
                "source_days": 2,
                "expected_source_days": 2,
                "first_opened_payload_date": "2019-07-01",
                "last_opened_payload_date": "2024-12-31",
                "decoded_m1": 200,
                "emitted_m5": 16,
                "dropped_partial_m5_buckets": 0,
                "confirmation_opened": True,
                "pre_oos_2025_opened": False,
                "protected_2026_opened": False,
                "output": str(generated_csv.resolve()),
                "output_sha256": "f" * 64,
            }

        with patch.object(m, "CANONICAL_OUTPUT_DIR", outdir), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress), \
             patch.object(m.stage, "_read_canonical_r15_index", return_value=index.read_bytes()), \
             patch.object(m.sealed_builder, "EXPECTED_SOURCE_DAYS", 2), \
             patch.object(m.sealed_builder, "build", side_effect=fake_build):
            payload = m.run_from_index(index, progress)

        assert payload["research"] == "R26"
        assert payload["stage"] == "confirmation"
        assert payload["confirmation_opened"] is True
        assert payload["pre_oos_2025_opened"] is False
        assert payload["protected_2026_opened"] is False
        assert payload["result"]["summary"]["event_count"] == 2
        assert all(e["research"] == "R26" for e in payload["result"]["events"])
        assert all(e["origin_research"] == "R24" for e in payload["result"]["events"])
        assert payload["confirmation_gate"]["primary_metrics"] == [
            "reversal_2b",
            "reversal_4b",
        ]
        assert payload["confirmation_gate"]["joint_gate"] == "ALL_REQUIRED"
        assert "reversal_8b" in payload["confirmation_gate"][
            "descriptive_metrics_cannot_rescue_primary"
        ]


def test_existing_confirmation_result_refuses_rerun():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r26_xau_confirmation_v100"
        root.mkdir(parents=True)
        output = root / "confirmation.json"
        progress = root / "progress.json"
        output.write_text('{"status":"EXISTING"}', encoding="utf-8")

        with patch.object(m, "CANONICAL_OUTPUT_DIR", root), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress):
            try:
                m.run_from_index(Path("unused.csv"), progress)
            except RuntimeError as exc:
                assert "refusing scientific overwrite" in str(exc)
            else:
                raise AssertionError("existing R26 result was overwritten")


def test_output_and_progress_paths_are_confined():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r26_xau_confirmation_v100"
        root.parent.mkdir(parents=True, exist_ok=True)
        output = root / "confirmation.json"
        progress = root / "progress.json"

        with patch.object(m, "CANONICAL_OUTPUT_DIR", root), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress):
            assert m._validate_output_path(output) == output.absolute()
            assert m._validate_progress_path(progress) == progress.absolute()
            try:
                m._validate_output_path(root / "other.json")
            except RuntimeError:
                pass
            else:
                raise AssertionError("non-canonical R26 output accepted")


def main():
    test_reuses_exact_frozen_components()
    test_joint_confirmation_gate_is_strict_and_fail_closed()
    test_frozen_r24_event_definition_yields_positive_reversal_both_directions()
    test_run_pipeline_is_r26_only_and_keeps_2025_2026_closed()
    test_existing_confirmation_result_refuses_rerun()
    test_output_and_progress_paths_are_confined()
    print("PASS: R26 opening-range reversal confirmation v1.00 tests")


if __name__ == "__main__":
    main()
