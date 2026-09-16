#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import xau_edge_discovery_r21_r25_v1_03 as discovery
import xau_r21_confirmation_v1_00 as stage
import xau_r27_confirmation_v1_00 as m


def test_reuses_exact_frozen_components():
    assert m.r27_event_extractor is discovery.r22_volatility_compression
    assert m.r27_complete_jackknife is discovery.r22_complete_estimator_day_jackknife
    assert m.sealed_builder is stage.sealed_builder


def _raw_jackknife(mean, t, reason=None):
    return {
        "n": 100,
        "clusters": 20,
        "baseline_days": 20,
        "event_days": 20,
        "required_replicates": 20,
        "valid_replicates": 20 if reason is None else 19,
        "undefined_delete_days": [] if reason is None else ["2020-01-01"],
        "mean": mean,
        "cluster_se": abs(mean / t) if mean is not None and t not in (None, 0) else None,
        "cluster_t": t,
        "method": "delete_one_utc_day_complete_estimator_fail_closed",
        "reason": reason,
    }


def test_persistence_transform_preserves_se_and_flips_mean_t():
    raw = _raw_jackknife(-0.0002, -4.0)
    out = m._persistence_stats(raw)
    assert out["mean"] == 0.0002
    assert out["cluster_t"] == 4.0
    assert out["cluster_se"] == raw["cluster_se"]
    assert out["required_replicates"] == 20
    assert out["sign_transform"] == "persistence = -excess_abs"


def test_joint_gate_is_strict_and_fail_closed():
    passed = {
        "persistence_4b": m._persistence_stats(_raw_jackknife(-0.0001, -2.01)),
        "persistence_8b": m._persistence_stats(_raw_jackknife(-0.0002, -3.0)),
    }
    assert m._confirmation_gate(passed)["status"] == "PASS"

    fail_cases = [
        {
            "persistence_4b": m._persistence_stats(_raw_jackknife(0.0, -5.0)),
            "persistence_8b": m._persistence_stats(_raw_jackknife(-0.0002, -3.0)),
        },
        {
            "persistence_4b": m._persistence_stats(_raw_jackknife(-0.0001, -2.0)),
            "persistence_8b": m._persistence_stats(_raw_jackknife(-0.0002, -3.0)),
        },
        {
            "persistence_4b": m._persistence_stats(_raw_jackknife(-0.0001, -3.0)),
            "persistence_8b": m._persistence_stats(_raw_jackknife(None, None, "undefined")),
        },
    ]
    for case in fail_cases:
        assert m._confirmation_gate(case)["status"] == "FAIL"


def test_naive_sign_transform_handles_zero_exactly():
    events = [
        {
            "compression_state": "bottom10",
            "excess_abs_4b": -1.0,
            "excess_abs_8b": -2.0,
        },
        {
            "compression_state": "bottom10",
            "excess_abs_4b": 0.0,
            "excess_abs_8b": 0.0,
        },
        {
            "compression_state": "bottom10",
            "excess_abs_4b": 1.0,
            "excess_abs_8b": 2.0,
        },
    ]
    stats = m._naive_primary(events)
    assert stats["persistence_4b"]["mean"] == 0.0
    assert stats["persistence_4b"]["positive_fraction"] == 1 / 3
    assert stats["persistence_8b"]["positive_fraction"] == 1 / 3


def _write_minimal_confirmation_csv(path: Path):
    rows = [
        (datetime(2019, 7, 1, 12, 20, tzinfo=timezone.utc), 1400.0),
        (datetime(2024, 12, 31, 13, 20, tzinfo=timezone.utc), 1500.0),
    ]
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
        for dt, price in rows:
            w.writerow({
                "symbol": "XAUUSD",
                "timeframe": "M5",
                "server_time": dt.isoformat(),
                "server_epoch": int(dt.timestamp()),
                "open": price,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price,
            })


def test_run_pipeline_uses_bottom10_joint_jackknife_only():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        index = root / "master_index.csv"
        index.write_bytes(b"verified pinned index bytes")

        outdir = root / "r27_xau_confirmation_v100"
        output = outdir / "confirmation.json"
        progress = outdir / "progress.json"

        def fake_build(index_path: Path, generated_csv: Path, progress_callback=None):
            assert index_path.read_bytes() == b"verified pinned index bytes"
            _write_minimal_confirmation_csv(generated_csv)
            if progress_callback:
                progress_callback({
                    "completed": 1,
                    "total": 2,
                    "last_opened_payload_date": "2019-07-01",
                    "decoded_m1": 100,
                    "emitted_m5": 1,
                })
                progress_callback({
                    "completed": 2,
                    "total": 2,
                    "last_opened_payload_date": "2024-12-31",
                    "decoded_m1": 200,
                    "emitted_m5": 2,
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
                "emitted_m5": 2,
                "dropped_partial_m5_buckets": 0,
                "confirmation_opened": True,
                "pre_oos_2025_opened": False,
                "protected_2026_opened": False,
                "output": str(generated_csv.resolve()),
                "output_sha256": "f" * 64,
            }

        fake_events = [
            {
                "research": "R22",
                "compression_state": "bottom10",
                "cluster_day": "2019-07-01",
                "utc_minute": 720,
                "abs_fwd_4b": 0.001,
                "abs_fwd_8b": 0.002,
                "excess_abs_4b": -0.0001,
                "excess_abs_8b": -0.0002,
            },
            {
                "research": "R22",
                "compression_state": "bottom20",
                "cluster_day": "2019-07-01",
                "utc_minute": 720,
                "abs_fwd_4b": 0.001,
                "abs_fwd_8b": 0.002,
                "excess_abs_4b": -0.00005,
                "excess_abs_8b": -0.00008,
            },
        ]

        def fake_jackknife(bars, events, state, horizon):
            assert state == "bottom10"
            assert horizon in (4, 8)
            return (
                _raw_jackknife(-0.0001, -3.0)
                if horizon == 4
                else _raw_jackknife(-0.0002, -4.0)
            )

        with patch.object(m, "CANONICAL_OUTPUT_DIR", outdir), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress), \
             patch.object(m.stage, "_read_canonical_r15_index", return_value=index.read_bytes()), \
             patch.object(m.sealed_builder, "EXPECTED_SOURCE_DAYS", 2), \
             patch.object(m.sealed_builder, "build", side_effect=fake_build), \
             patch.object(m, "r27_event_extractor", return_value=fake_events), \
             patch.object(m, "r27_complete_jackknife", side_effect=fake_jackknife):
            payload = m.run_from_index(index, progress)

        assert payload["research"] == "R27"
        assert payload["confirmation_gate"]["status"] == "PASS"
        assert payload["event_count_bottom10"] == 1
        assert payload["event_count_all_states"] == 2
        assert all(e["research"] == "R27" for e in payload["events"])
        assert all(e["origin_research"] == "R22" for e in payload["events"])
        assert payload["pre_oos_2025_opened"] is False
        assert payload["protected_2026_opened"] is False
        assert payload["primary_complete_jackknife"]["persistence_4b"]["mean"] == 0.0001
        assert payload["primary_complete_jackknife"]["persistence_8b"]["cluster_t"] == 4.0


def test_existing_confirmation_result_refuses_rerun():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r27_xau_confirmation_v100"
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
                raise AssertionError("existing R27 result was overwritten")


def test_output_and_progress_paths_are_confined():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r27_xau_confirmation_v100"
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
                raise AssertionError("non-canonical R27 output accepted")


def main():
    test_reuses_exact_frozen_components()
    test_persistence_transform_preserves_se_and_flips_mean_t()
    test_joint_gate_is_strict_and_fail_closed()
    test_naive_sign_transform_handles_zero_exactly()
    test_run_pipeline_uses_bottom10_joint_jackknife_only()
    test_existing_confirmation_result_refuses_rerun()
    test_output_and_progress_paths_are_confined()
    print("PASS: R27 compression-persistence confirmation v1.00 tests")


if __name__ == "__main__":
    main()
