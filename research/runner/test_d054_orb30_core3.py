#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "runner"))

import d053_orb30_deep_audit as audit053
import d054_orb30_core3_workflow as d054
import experiment
import runner


def row(symbol: str, day: str, side: str, net: float, stress: float) -> dict[str, str]:
    return {
        "symbol": symbol,
        "day_key": day,
        "side": side,
        "net_r": str(net),
        "net_r_spread_x1_5": str(stress),
        "mfe_r": "0.8",
        "mae_r": "0.4",
    }


def synthetic_batch(value: float, stress: float) -> dict:
    temp = Path(tempfile.mkdtemp(prefix="d054_test_"))
    tests = []
    fields = ["symbol", "day_key", "side", "net_r", "net_r_spread_x1_5", "mfe_r", "mae_r"]
    for si, symbol in enumerate(d054.SYMBOLS):
        path = temp / f"{symbol}.csv"
        rows = []
        for i in range(40):
            day = f"202607{(i % 20) + 1:02d}" if i < 20 else f"202608{(i % 20) + 1:02d}"
            rows.append(row(symbol, day, "LONG" if (i + si) % 2 == 0 else "SHORT", value, stress))
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
        tests.append({"symbol": symbol, "trades": {"path": str(path)}, "integrity": {"integrity_events": 0}})
    return {"tests": tests}


def synthetic_month_failure_batch() -> dict:
    temp = Path(tempfile.mkdtemp(prefix="d054_month_fail_"))
    tests = []
    fields = ["symbol", "day_key", "side", "net_r", "net_r_spread_x1_5", "mfe_r", "mae_r"]
    for si, symbol in enumerate(d054.SYMBOLS):
        path = temp / f"{symbol}.csv"
        rows = []
        for i in range(40):
            july = i < 20
            day = f"202607{(i % 20) + 1:02d}" if july else f"202608{(i % 20) + 1:02d}"
            value = -0.02 if july else 0.20
            rows.append(row(symbol, day, "LONG" if (i + si) % 2 == 0 else "SHORT", value, value - 0.01))
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
        tests.append({"symbol": symbol, "trades": {"path": str(path)}, "integrity": {"integrity_events": 0}})
    return {"tests": tests}


def test_identity_and_closed_frozen_gates() -> None:
    manifest_path, manifest = experiment.load_manifest("D054")
    assert manifest_path.name == "D054.json"
    assert manifest["experiment_id"] == d054.EXPERIMENT_ID
    assert manifest["status"] == "UNCONFIRMED"
    assert manifest["stages"]["confirmation"]["status"] == "FAIL"
    assert manifest["stages"]["confirmation"]["gates"] == d054.FROZEN_CONFIRMATION_GATES
    assert manifest["results"]["final_verdict"] == "D054_UNCONFIRMED_CLOSE"
    assert d054.git_blob_sha(d054.PREREG) == d054.EXPECTED_PREREG_BLOB
    assert d054.git_blob_sha(d054.SOURCE) == d054.EXPECTED_SOURCE_BLOB
    source_sha = runner.source_identity_sha256(ROOT / d054.SOURCE, runner.SOURCE_SHA_MODE_TEXT_LF)
    assert source_sha == d054.EXPECTED_SOURCE_SHA256
    assert d054.SYMBOLS == ["SPX500", "NDX100", "US30"]
    assert d054.HOLDOUT_FROM == "2026-07-01"
    assert d054.HOLDOUT_TO == "2026-08-31"
    assert d054.FROZEN_CONFIRMATION_GATES == {
        "aggregate_n_min": 100,
        "each_symbol_n_min": 25,
        "aggregate_mean_net_r_positive": True,
        "aggregate_pf_min": 1.05,
        "aggregate_total_net_r_positive": True,
        "spread_stress_total_positive": True,
        "positive_symbols_min": 2,
        "july_total_positive": True,
        "august_total_positive": True,
        "long_mean_positive": True,
        "short_mean_positive": True,
        "day_block_bootstrap_lower_95_positive": True,
        "max_positive_symbol_contribution_share": 0.70,
        "integrity_events_max": 0,
    }


def test_positive_confirmation_passes() -> None:
    original = d054.BOOTSTRAP_REPS
    d054.BOOTSTRAP_REPS = 1000
    try:
        score = d054.score_confirmation(synthetic_batch(0.10, 0.08))
    finally:
        d054.BOOTSTRAP_REPS = original
    assert score["status"] == "D054_CONFIRMED_CORE3_ENTRY_ALPHA", score
    assert score["all_gates_pass"] is True
    assert score["metrics"]["positive_symbols_n"] == 3
    assert score["gates"]["july_total_positive"] is True
    assert score["gates"]["august_total_positive"] is True
    assert score["gates"]["long_mean_positive"] is True
    assert score["gates"]["short_mean_positive"] is True


def test_negative_confirmation_fails() -> None:
    original = d054.BOOTSTRAP_REPS
    d054.BOOTSTRAP_REPS = 1000
    try:
        score = d054.score_confirmation(synthetic_batch(-0.10, -0.12))
    finally:
        d054.BOOTSTRAP_REPS = original
    assert score["status"] == "D054_UNCONFIRMED_CLOSE", score
    assert score["all_gates_pass"] is False
    assert score["gates"]["aggregate_mean_net_r_positive"] is False


def test_one_negative_month_cannot_be_hidden_by_good_aggregate() -> None:
    original = d054.BOOTSTRAP_REPS
    d054.BOOTSTRAP_REPS = 1000
    try:
        score = d054.score_confirmation(synthetic_month_failure_batch())
    finally:
        d054.BOOTSTRAP_REPS = original
    assert score["metrics"]["aggregate_total_net_r"] > 0
    assert score["gates"]["july_total_positive"] is False
    assert score["status"] == "D054_UNCONFIRMED_CLOSE"


def test_dst_proxy_has_mismatch_and_alignment() -> None:
    from datetime import date
    assert audit053.dst_mismatch_proxy(date(2024, 3, 15)) is True
    assert audit053.dst_mismatch_proxy(date(2024, 4, 15)) is False


if __name__ == "__main__":
    test_identity_and_closed_frozen_gates()
    test_positive_confirmation_passes()
    test_negative_confirmation_fails()
    test_one_negative_month_cannot_be_hidden_by_good_aggregate()
    test_dst_proxy_has_mismatch_and_alignment()
    print("D054_TESTS_OK")
