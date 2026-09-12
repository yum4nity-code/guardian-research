#!/usr/bin/env python3
from __future__ import annotations

"""Infrastructure-only wrapper for the frozen R6 protected-2026 OOS executor.

Scientific semantics remain in v1_01. This revision fixes only datetime -> epoch
conversion inside the inherited news-mask transport. pandas datetime integer storage
resolution may be seconds, microseconds, or nanoseconds depending on construction
and version, so dividing Series.astype('int64') by 1e9 is not resolution-safe.
Timestamp.value is explicitly nanoseconds and therefore gives stable epoch seconds.
"""

import numpy as np
import pandas as pd

import r6_protected_2026_oos_v1_01 as base


def epoch_seconds(series: pd.Series) -> np.ndarray:
    return np.fromiter(
        (int(pd.Timestamp(v).value // 1_000_000_000) for v in series),
        dtype=np.int64,
        count=len(series),
    )


def apply_news_mask(source: pd.DataFrame, intervals) -> pd.DataFrame:
    epochs = epoch_seconds(source.time)
    keep = np.ones(len(source), dtype=bool)
    j = 0
    for i, t in enumerate(epochs):
        while j < len(intervals) and intervals[j][1] < t:
            j += 1
        if j < len(intervals) and intervals[j][0] <= t <= intervals[j][1]:
            keep[i] = False
    out = source.loc[keep].reset_index(drop=True)
    if len(out) < 30000:
        raise RuntimeError(f"news-clean M5 snapshot too short: {len(out)}")
    return out


# Patch only the transport helper used by the frozen v1_01 main routine.
# No scientific rule, candidate, gate, period, cost profile, or statistic changes.
base.apply_news_mask = apply_news_mask


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
