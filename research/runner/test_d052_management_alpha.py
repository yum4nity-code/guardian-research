#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "runner"))

import d052_management_alpha_workflow as d052


def test_frozen_contract() -> None:
    assert d052.REFERENCE == "REF_EOD_NO_STOP"
    assert len(d052.MANAGEMENTS) == 12
    assert len(d052.CANDIDATES) == 11
    assert len(set(d052.MANAGEMENTS)) == 12
    assert len(d052.SYMBOLS) == 12
    assert d052.SMOKE_SYMBOLS == ["EURUSD", "SPX500", "XAUUSD"]
    assert (d052.DEV_FROM, d052.DEV_TO) == ("2024-01-02", "2025-12-31")
    assert (d052.HOLDOUT_FROM, d052.HOLDOUT_TO) == ("2026-07-01", "2026-08-31")
    assert "XPTUSD" not in d052.SYMBOLS
    assert not any(s.endswith("USD") and s.startswith(("BTC", "ETH")) for s in d052.SYMBOLS)


def test_committed_identity_contract() -> None:
    identities = d052.verify_frozen_repository_identity()
    assert identities[d052.PREREG] == d052.PREREG_GIT_BLOB_SHA
    assert identities[d052.SOURCE] == d052.SOURCE_GIT_BLOB_SHA


def test_manifest_lock() -> None:
    source_sha = d052.runner.source_identity_sha256(
        ROOT / d052.SOURCE, d052.runner.SOURCE_SHA_MODE_TEXT_LF
    )
    path, manifest = d052.build_manifest(source_sha)
    assert path.is_file()
    assert manifest["experiment_id"] == d052.EXPERIMENT_ID
    assert manifest["source"]["source_sha256"] == source_sha
    assert manifest["stages"]["development"]["status"] == "LOCKED_UNTIL_SMOKE_PASS"
    assert manifest["stages"]["confirmation"]["status"] == "UNOPENED"
    assert manifest["stages"]["confirmation"]["from"] == d052.HOLDOUT_FROM
    gates = manifest["stages"]["development"]["gates"]
    assert gates["candidate_n_min"] == 8000
    assert gates["each_symbol_n_min"] == 600
    assert gates["positive_symbols_min"] == 9
    assert math.isclose(gates["max_positive_symbol_share"], 0.25)


def test_bootstrap_determinism() -> None:
    blocks = {
        "202401": [0.1, 0.2, 0.3],
        "202402": [0.2, 0.1, 0.4],
        "202403": [0.3, 0.2, 0.2],
        "202404": [0.4, 0.1, 0.3],
        "202405": [0.2, 0.2, 0.2],
        "202406": [0.3, 0.3, 0.1],
    }
    a = d052.block_bootstrap_ci(blocks, 1000, 52052)
    b = d052.block_bootstrap_ci(blocks, 1000, 52052)
    assert a == b
    assert a["lower_95"] > 0
    assert a["lower_95"] <= a["median"] <= a["upper_95"]


def test_source_contains_frozen_matrix() -> None:
    text = (ROOT / d052.SOURCE).read_text(encoding="utf-8")
    for name in d052.MANAGEMENTS:
        assert f'"{name}"' in text
    for symbol in d052.SYMBOLS:
        assert f'"{symbol}"' in text
    assert "NO ORDERS" in text
    assert "StableScheduleHash" in text
    assert "ScheduleMinute" in text
    assert "OpenPairedEvent" in text
    assert "Model0 required" in text


def main() -> int:
    test_frozen_contract()
    test_committed_identity_contract()
    test_manifest_lock()
    test_bootstrap_determinism()
    test_source_contains_frozen_matrix()
    print("D052_MANAGEMENT_ALPHA_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
