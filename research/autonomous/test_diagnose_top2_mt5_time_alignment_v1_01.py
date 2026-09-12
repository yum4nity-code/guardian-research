#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import diagnose_top2_mt5_time_alignment_v1_01 as d


def main():
    # Regression for generation-65 bug: MT5 series may be stored as microseconds
    # while pandas.Timestamp.value is nanoseconds. The diagnostic must normalize
    # both sides before subtraction.
    canon = pd.Series(pd.to_datetime([
        "2024-01-02T10:00:00Z",
        "2024-01-02T11:00:00Z",
    ], utc=True))
    mt5 = pd.Series(pd.array([
        "2024-01-02T11:00:00Z",
        "2024-01-02T12:00:00Z",
    ], dtype="datetime64[us, UTC]"))

    assert str(mt5.dtype) == "datetime64[us, UTC]", mt5.dtype
    assert d.nearest_offsets_hours(canon, mt5) == [1.0, 0.0]

    # Deliberately use a one-to-one shifted pair to test exact matching logic.
    cdf = pd.DataFrame({
        "entry_time": pd.to_datetime(["2024-01-02T10:00:00Z"], utc=True),
        "exit_time": pd.to_datetime(["2024-01-02T10:30:00Z"], utc=True),
    })
    mdf = pd.DataFrame({
        "entry_time": pd.array(["2024-01-02T11:00:00Z"], dtype="datetime64[us, UTC]"),
        "exit_time": pd.array(["2024-01-02T11:30:00Z"], dtype="datetime64[us, UTC]"),
    })
    shifted = d.exact_after_shift(cdf, mdf, 1.0)
    assert shifted["exact_entry_matches"] == 1
    assert shifted["exact_pair_matches"] == 1

    # Protected-period regression: this unit test contains no 2026 market data
    # and the diagnostic implementation exposes no argument that widens its
    # hard-coded YEARS=(2024, 2025) comparison set.
    assert d.YEARS == (2024, 2025)
    assert d.CANDIDATES == ("R6B-347", "R6B-307")

    print("PASS resolution-safe TOP2 MT5 time-alignment diagnostic regression")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
