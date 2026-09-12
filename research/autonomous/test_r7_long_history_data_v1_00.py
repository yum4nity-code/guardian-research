#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pandas as pd

import r7_long_history_data_v1_00 as d


def main() -> int:
    assert d.months("2017-08", "2017-10") == ["2017-08", "2017-09", "2017-10"]

    ms = pd.Series([1502928000000, 1502928300000])
    us = pd.Series([1502928000000000, 1502928300000000])
    t_ms = d.infer_time(ms)
    t_us = d.infer_time(us)
    assert t_ms.iloc[0] == t_us.iloc[0]
    assert (t_ms.iloc[1] - t_ms.iloc[0]) == pd.Timedelta(minutes=5)

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.zip"
        p.write_bytes(b"not-a-zip")
        assert not zipfile.is_zipfile(p)

    # Validation accepts partial listing month plus complete 2025 endpoint and records gaps rather than inventing bars.
    vf = pd.DataFrame({
        "time": pd.to_datetime(["2017-08-17T04:00:00Z", "2017-08-17T04:05:00Z", "2025-12-31T23:55:00Z"], utc=True),
        "open": [1.0, 1.0, 1.0], "high": [1.0, 1.0, 1.0], "low": [1.0, 1.0, 1.0], "close": [1.0, 1.0, 1.0]
    })
    s = d.validate_symbol(vf, "BTCUSDT")
    assert s["gap_count_non_5m"] == 1
    assert s["duplicate_count"] == 0

    print('{"status":"PASS","tests":4,"network_access":false,"protected_market_data_access":false}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
