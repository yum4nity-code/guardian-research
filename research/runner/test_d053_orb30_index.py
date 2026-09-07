#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "runner"))

# Import the operator entrypoint so the frozen v1.01 identity overrides are
# applied exactly as they are during the real local workflow.
import d053_orb30_index_run as d053_run

d053 = d053_run.d053


def row(symbol: str, day: str, side: str, net: float, stress: float) -> dict[str, str]:
    return {
        "symbol": symbol,
        "day_key": day,
        "side": side,
        "net_r": str(net),
        "net_r_spread_x1_5": str(stress),
        "mfe_r": "0.5",
        "mae_r": "0.2",
    }


def build_rows(value: float, stress: float) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    months = [f"{year}{month:02d}" for year in (2024, 2025) for month in range(1, 13)]
    for symbol_index, symbol in enumerate(d053.SYMBOLS):
        for i in range(250):
            month = months[i % len(months)]
            day = f"{month}{(i % 27) + 1:02d}"
            side = "LONG" if (i + symbol_index) % 2 == 0 else "SHORT"
            rows.append(row(symbol, day, side, value, stress))
    return rows


def test_frozen_source_sha() -> None:
    path = ROOT / d053.SOURCE
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert actual == d053.EXPECTED_SOURCE_SHA256, (actual, d053.EXPECTED_SOURCE_SHA256)
    assert d053.SOURCE_VERSION == "1.01"


def test_positive_population_passes() -> None:
    original = d053.BOOTSTRAP_REPS
    d053.BOOTSTRAP_REPS = 1000
    try:
        score = d053.score_rows(build_rows(0.10, 0.08), 0)
    finally:
        d053.BOOTSTRAP_REPS = original
    assert score["status"] == "D053_DEV_PASS_HOLDOUT_LOCKED", score
    assert score["all_gates_pass"] is True
    assert score["holdout"]["opened_by_this_workflow"] is False


def test_negative_population_rejects() -> None:
    original = d053.BOOTSTRAP_REPS
    d053.BOOTSTRAP_REPS = 1000
    try:
        score = d053.score_rows(build_rows(-0.10, -0.12), 0)
    finally:
        d053.BOOTSTRAP_REPS = original
    assert score["status"] == "D053_REJECT_V0", score
    assert score["all_gates_pass"] is False
    assert score["gates"]["aggregate_mean_net_r_min"] is False
    assert score["holdout"]["status"] == "LOCKED_UNOPENED"


if __name__ == "__main__":
    test_frozen_source_sha()
    test_positive_population_passes()
    test_negative_population_rejects()
    print("D053_TESTS_OK_V101")
