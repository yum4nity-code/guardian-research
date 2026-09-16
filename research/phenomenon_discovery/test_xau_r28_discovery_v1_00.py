#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import xau_edge_discovery_r21_r25_v1_03 as discovery
import xau_r28_discovery_v1_00 as m


def test_reuses_exact_r22_state_and_forward_return():
    assert m.r28_event_extractor is discovery.r22_volatility_compression
    assert m.forward_return is discovery.base.forward_return


def test_event_signed_forward_returns_filters_bottom10_and_preserves_origin():
    start = datetime(2019, 1, 2, 0, 0, tzinfo=timezone.utc)
    bars = [
        m.Bar(
            int((start + timedelta(minutes=5*i)).timestamp()),
            start + timedelta(minutes=5*i),
            "M5",
            100.0,
            101.0,
            99.0,
            100.0 + i,
        )
        for i in range(10)
    ]
    raw = [
        {
            "research": "R22",
            "compression_state": "bottom10",
            "epoch": bars[0].epoch,
            "cluster_day": bars[0].utc_day,
            "utc_minute": bars[0].utc_minute,
            "year": 2019,
        },
        {
            "research": "R22",
            "compression_state": "bottom20",
            "epoch": bars[0].epoch,
            "cluster_day": bars[0].utc_day,
            "utc_minute": bars[0].utc_minute,
            "year": 2019,
        },
    ]
    events = m._event_signed_forward_returns(bars, raw)
    assert len(events) == 1
    assert events[0]["research"] == "R28"
    assert events[0]["origin_research"] == "R22"
    assert events[0]["signed_fwd_4b"] == bars[4].close / bars[0].close - 1.0
    assert events[0]["signed_fwd_8b"] == bars[8].close / bars[0].close - 1.0


def test_complete_signed_estimator_recomputes_same_clock_baseline():
    events = [
        {
            "cluster_day": "2020-01-01",
            "utc_minute": 60,
            "signed_fwd_4b": 0.03,
        },
        {
            "cluster_day": "2020-01-02",
            "utc_minute": 60,
            "signed_fwd_4b": 0.05,
        },
        {
            "cluster_day": "2020-01-03",
            "utc_minute": 60,
            "signed_fwd_4b": 0.07,
        },
    ]
    baseline = [
        ("2020-01-01", 60, 0.01),
        ("2020-01-02", 60, 0.02),
        ("2020-01-03", 60, 0.03),
    ]

    with patch.object(m, "_signed_baseline_observations", return_value=baseline):
        out = m.complete_signed_excess_day_jackknife([], events, 4)

    # Full event mean .05 minus baseline mean .02 = .03.
    assert abs(out["mean"] - 0.03) < 1e-15
    assert out["required_replicates"] == 3
    assert out["valid_replicates"] == 3
    assert out["undefined_delete_days"] == []
    assert out["cluster_se"] is not None
    assert out["cluster_t"] is not None
    assert out["reason"] is None


def test_complete_signed_estimator_fails_closed_if_required_delete_is_undefined():
    events = [
        {
            "cluster_day": "2020-01-01",
            "utc_minute": 60,
            "signed_fwd_4b": 0.03,
        }
    ]
    # Only one baseline observation at the required event clock. Deleting its
    # day makes the baseline at that clock undefined.
    baseline = [
        ("2020-01-01", 60, 0.01),
        ("2020-01-02", 120, 0.02),
    ]

    with patch.object(m, "_signed_baseline_observations", return_value=baseline):
        out = m.complete_signed_excess_day_jackknife([], events, 4)

    assert out["mean"] is not None
    assert out["cluster_se"] is None
    assert out["cluster_t"] is None
    assert out["valid_replicates"] < out["required_replicates"]
    assert out["undefined_delete_days"]
    assert "undefined" in out["reason"]


def _stats(mean, t, reason=None):
    return {
        "mean": mean,
        "cluster_t": t,
        "reason": reason,
        "required_replicates": 100,
        "valid_replicates": 100 if reason is None else 99,
        "undefined_delete_days": [] if reason is None else ["x"],
    }


def test_discovery_gate_requires_same_sign_and_both_abs_t_above_2():
    positive = {
        "directional_excess_4b": _stats(0.0001, 2.1),
        "directional_excess_8b": _stats(0.0002, 3.0),
    }
    g = m.discovery_gate(positive)
    assert g["status"] == "PASS"
    assert g["frozen_confirmation_sign"] == 1

    negative = {
        "directional_excess_4b": _stats(-0.0001, -2.1),
        "directional_excess_8b": _stats(-0.0002, -3.0),
    }
    g = m.discovery_gate(negative)
    assert g["status"] == "PASS"
    assert g["frozen_confirmation_sign"] == -1

    mismatched = {
        "directional_excess_4b": _stats(0.0001, 3.0),
        "directional_excess_8b": _stats(-0.0001, -3.0),
    }
    assert m.discovery_gate(mismatched)["status"] == "FAIL"

    boundary = {
        "directional_excess_4b": _stats(0.0001, 2.0),
        "directional_excess_8b": _stats(0.0002, 3.0),
    }
    assert m.discovery_gate(boundary)["status"] == "FAIL"

    undefined = {
        "directional_excess_4b": _stats(None, None, "undefined"),
        "directional_excess_8b": _stats(0.0002, 3.0),
    }
    assert m.discovery_gate(undefined)["status"] == "FAIL"


def test_full_sample_baseline_attachment_is_descriptive_only_and_signed():
    start = datetime(2019, 1, 2, 0, 0, tzinfo=timezone.utc)
    bars = [
        m.Bar(
            int((start + timedelta(minutes=5*i)).timestamp()),
            start + timedelta(minutes=5*i),
            "M5",
            100.0,
            101.0,
            99.0,
            100.0 + i,
        )
        for i in range(12)
    ]
    events = [{
        "utc_minute": bars[0].utc_minute,
        "signed_fwd_4b": bars[4].close / bars[0].close - 1.0,
        "signed_fwd_8b": bars[8].close / bars[0].close - 1.0,
    }]
    m._attach_full_sample_baselines(bars, events)
    assert events[0]["baseline_signed_4b"] is not None
    assert events[0]["baseline_signed_8b"] is not None
    assert abs(
        events[0]["directional_excess_4b"]
        - (
            events[0]["signed_fwd_4b"]
            - events[0]["baseline_signed_4b"]
        )
    ) < 1e-15


def test_existing_discovery_result_refuses_rerun():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r28_xau_discovery_v100"
        root.mkdir(parents=True)
        output = root / "discovery.json"
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
                raise AssertionError("existing R28 discovery result was overwritten")


def test_output_and_progress_paths_are_confined():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r28_xau_discovery_v100"
        root.parent.mkdir(parents=True, exist_ok=True)
        output = root / "discovery.json"
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
                raise AssertionError("non-canonical R28 output accepted")


def main():
    test_reuses_exact_r22_state_and_forward_return()
    test_event_signed_forward_returns_filters_bottom10_and_preserves_origin()
    test_complete_signed_estimator_recomputes_same_clock_baseline()
    test_complete_signed_estimator_fails_closed_if_required_delete_is_undefined()
    test_discovery_gate_requires_same_sign_and_both_abs_t_above_2()
    test_full_sample_baseline_attachment_is_descriptive_only_and_signed()
    test_existing_discovery_result_refuses_rerun()
    test_output_and_progress_paths_are_confined()
    print("PASS: R28 compression-state directional discovery v1.00 tests")


if __name__ == "__main__":
    main()
