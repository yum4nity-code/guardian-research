#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import xau_edge_discovery_r21_r25_v1_01 as base
import xau_r21_confirmation_v1_00 as m


def test_reuses_exact_frozen_r21_extractor():
    assert m.r21_comex_unconditional_drift is base.r21_comex_unconditional_drift


def test_confirmation_gate_pass_and_fail_closed():
    passed = {
        "metrics": {
            "post_15m": {
                "clustered": {
                    "mean": 0.0001,
                    "cluster_t": 2.01,
                }
            }
        }
    }
    failed_t = {
        "metrics": {
            "post_15m": {
                "clustered": {
                    "mean": 0.0001,
                    "cluster_t": 2.0,
                }
            }
        }
    }
    failed_mean = {
        "metrics": {
            "post_15m": {
                "clustered": {
                    "mean": 0.0,
                    "cluster_t": 5.0,
                }
            }
        }
    }
    unavailable = {
        "metrics": {
            "post_15m": {
                "clustered": {
                    "mean": None,
                    "cluster_t": None,
                }
            }
        }
    }

    assert m._confirmation_gate(passed)["status"] == "PASS"
    assert m._confirmation_gate(failed_t)["status"] == "FAIL"
    assert m._confirmation_gate(failed_mean)["status"] == "FAIL"
    assert m._confirmation_gate(unavailable)["status"] == "FAIL"


def _write_bar_csv(path: Path, rows):
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
                "high": price + 0.1,
                "low": price - 0.1,
                "close": price,
            })


def test_confirmation_loader_rejects_outside_window_and_off_grid():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        outside = root / "outside.csv"
        dt = datetime(2025, 1, 2, 12, 20, tzinfo=timezone.utc)
        _write_bar_csv(outside, [(dt, 1400.0)])
        try:
            m.load_generated_confirmation_bars(outside)
        except RuntimeError as exc:
            assert "escaped frozen window" in str(exc)
        else:
            raise AssertionError("2025 M5 row accepted")

        offgrid = root / "offgrid.csv"
        dt = datetime(2020, 1, 2, 13, 20, 30, tzinfo=timezone.utc)
        _write_bar_csv(offgrid, [(dt, 1400.0)])
        try:
            m.load_generated_confirmation_bars(offgrid)
        except RuntimeError as exc:
            assert "off-grid M5 timestamp" in str(exc)
        else:
            raise AssertionError("off-grid M5 row accepted")


def test_builder_receipt_rejects_2025_claim():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "generated.csv"
        p.write_text("x", encoding="utf-8")
        receipt = {
            "status": "PASS",
            "stage": "confirmation",
            "stage_start": m.CONFIRMATION_START.isoformat(),
            "stage_end_inclusive": m.CONFIRMATION_END.isoformat(),
            "source_days": m.sealed_builder.EXPECTED_SOURCE_DAYS,
            "expected_source_days": m.sealed_builder.EXPECTED_SOURCE_DAYS,
            "confirmation_opened": True,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            "output": str(p.resolve()),
            "first_opened_payload_date": "2019-07-01",
            "last_opened_payload_date": "2025-01-02",
        }
        try:
            m._validate_builder_receipt(receipt, p)
        except RuntimeError as exc:
            assert "last_opened_payload_date" in str(exc)
        else:
            raise AssertionError("receipt claiming 2025 payload was accepted")


def test_run_pipeline_uses_confirmation_only_and_writes_gate():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        index = root / "master_index.csv"
        index_bytes = b"pinned metadata"
        index.write_bytes(index_bytes)

        outdir = root / "r21_xau_confirmation_v100"
        output = outdir / "confirmation.json"
        progress = outdir / "progress.json"

        def fake_build(index_path: Path, generated_csv: Path, progress_callback=None):
            assert index_path.read_bytes() == index_bytes

            # Two synthetic event days placed on the exact confirmation boundaries.
            rows = []
            starts_and_gains = (
                (datetime(2019, 7, 1, 12, 20, tzinfo=timezone.utc), 1.0),
                (datetime(2024, 12, 31, 13, 20, tzinfo=timezone.utc), 2.0),
            )
            for start, gain in starts_and_gains:
                prices = [1400.0, 1400.0, 1400.0, 1400.0 + gain]
                for i, price in enumerate(prices):
                    rows.append((start + timedelta(minutes=5 * i), price))

            _write_bar_csv(generated_csv, rows)

            if progress_callback:
                progress_callback({
                    "completed": 1,
                    "total": 2,
                    "last_opened_payload_date": "2019-07-01",
                    "decoded_m1": 100,
                    "emitted_m5": 4,
                })
                progress_callback({
                    "completed": 2,
                    "total": 2,
                    "last_opened_payload_date": "2024-12-31",
                    "decoded_m1": 200,
                    "emitted_m5": 8,
                })

            return {
                "status": "PASS",
                "stage": "confirmation",
                "stage_start": m.CONFIRMATION_START.isoformat(),
                "stage_end_inclusive": m.CONFIRMATION_END.isoformat(),
                "source_days": 2,
                "expected_source_days": 2,
                "first_opened_payload_date": "2019-07-01",
                "last_opened_payload_date": "2024-12-31",
                "decoded_m1": 200,
                "emitted_m5": 8,
                "dropped_partial_m5_buckets": 0,
                "confirmation_opened": True,
                "pre_oos_2025_opened": False,
                "protected_2026_opened": False,
                "output": str(generated_csv.resolve()),
                "output_sha256": "f" * 64,
            }

        digest = hashlib.sha256(index_bytes).hexdigest()

        with patch.object(m, "CANONICAL_R15_INDEX", index), \
             patch.object(m, "CANONICAL_R15_INDEX_SHA256", digest), \
             patch.object(m, "_validate_pin_attestation", return_value={}), \
             patch.object(m, "CANONICAL_OUTPUT_DIR", outdir), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress), \
             patch.object(m.sealed_builder, "EXPECTED_SOURCE_DAYS", 2), \
             patch.object(m.sealed_builder, "build", side_effect=fake_build):
            payload = m.run_from_index(index, progress)

        assert payload["stage"] == "confirmation"
        assert payload["confirmation_opened"] is True
        assert payload["pre_oos_2025_opened"] is False
        assert payload["protected_2026_opened"] is False
        assert payload["result"]["summary"]["event_count"] == 2
        assert payload["confirmation_gate"]["primary_metric"] == "post_15m"
        assert payload["confirmation_gate"]["frozen_requirements"] == {
            "mean_gt": 0.0,
            "day_clustered_t_gt": 2.0,
        }
        assert "post_30m" in payload["confirmation_gate"]["descriptive_metrics_cannot_rescue_primary"]



def test_pin_attestation_requires_full_frozen_provenance():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "attestation.json"
        p.write_text(
            m.json.dumps({
                "status": "PASS",
                "phase": "r15-dukascopy-xauusd-boundary-union",
                "payload_count": 5517,
                "eligible_boundary_days": 5518,
                "known_missing_or_holiday_weekdays": 0,
                "payload_index_csv_sha256": m.CANONICAL_R15_INDEX_SHA256,
                "protected_2026_opened": False,
                "window": {
                    "start": "2004-11-08",
                    "end_exclusive": "2026-01-01",
                },
            }),
            encoding="utf-8",
        )
        with patch.object(m, "R15_PIN_ATTESTATION", p):
            try:
                m._validate_pin_attestation()
            except RuntimeError as exc:
                assert "payload_count" in str(exc)
            else:
                raise AssertionError("incomplete R15 provenance was accepted")


def test_existing_confirmation_result_refuses_rerun():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r21_xau_confirmation_v100"
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
                raise AssertionError("existing confirmation result was overwritten")


def test_output_and_progress_paths_are_confined():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r21_xau_confirmation_v100"
        root.parent.mkdir(parents=True, exist_ok=True)
        output = root / "confirmation.json"
        progress = root / "progress.json"

        with patch.object(m, "CANONICAL_OUTPUT_DIR", root), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress):
            assert m._validate_output_path(output) == output.absolute()
            assert m._validate_progress_path(progress) == progress.absolute()

            bad = root / "other.json"
            try:
                m._validate_output_path(bad)
            except RuntimeError:
                pass
            else:
                raise AssertionError("non-canonical output accepted")


def main():
    test_reuses_exact_frozen_r21_extractor()
    test_confirmation_gate_pass_and_fail_closed()
    test_confirmation_loader_rejects_outside_window_and_off_grid()
    test_builder_receipt_rejects_2025_claim()
    test_run_pipeline_uses_confirmation_only_and_writes_gate()
    test_pin_attestation_requires_full_frozen_provenance()
    test_existing_confirmation_result_refuses_rerun()
    test_output_and_progress_paths_are_confined()
    print("PASS: R21 confirmation v1.00 tests")


if __name__ == "__main__":
    main()
