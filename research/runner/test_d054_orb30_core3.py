#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "runner"))

import d053_orb30_deep_audit as audit053
import d054_orb30_core3_workflow as d054


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
    import tempfile
    import csv
    import tester

    temp = Path(tempfile.mkdtemp(prefix="d054_test_"))
    tests = []
    for si, symbol in enumerate(d054.SYMBOLS):
        path = temp / f"{symbol}.csv"
        fields = ["symbol", "day_key", "side", "net_r", "net_r_spread_x1_5", "mfe_r", "mae_r"]
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


def test_identity() -> None:
    ids = d054.verify_frozen_repository_identity()
    assert ids["source_sha256"] == d054.EXPECTED_SOURCE_SHA256
    assert d054.SYMBOLS == ["SPX500", "NDX100", "US30"]
    assert d054.HOLDOUT_FROM == "2026-07-01"
    assert d054.HOLDOUT_TO == "2026-08-31"


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


def test_dst_proxy_has_mismatch_and_alignment() -> None:
    from datetime import date
    assert audit053.dst_mismatch_proxy(date(2024, 3, 15)) is True
    assert audit053.dst_mismatch_proxy(date(2024, 4, 15)) is False


if __name__ == "__main__":
    test_identity()
    test_positive_confirmation_passes()
    test_negative_confirmation_fails()
    test_dst_proxy_has_mismatch_and_alignment()
    print("D054_TESTS_OK")
