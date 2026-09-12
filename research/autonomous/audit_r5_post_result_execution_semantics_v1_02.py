#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import audit_r5_post_result_execution_semantics_v1_00 as base


def _utc_ns(series: pd.Series) -> np.ndarray:
    """Return UTC timestamps as int64 nanoseconds, independent of pandas storage resolution."""
    idx = pd.DatetimeIndex(pd.to_datetime(series, utc=True))
    return idx.as_unit('ns').asi8


def raw_m1_reference_return(
    source_df: pd.DataFrame,
    source_atr: pd.Series,
    raw_m1_df: pd.DataFrame,
    horizon: int,
    direction: int,
    tf_seconds: int,
) -> np.ndarray:
    """Infrastructure-equivalent repair using explicit nanosecond timestamps.

    Scientific semantics are unchanged: entry is the first raw-M1 open at/after
    source-bar close; exit is the first raw-M1 open at/after the frozen source
    t+h+1 timestamp; signal/entry/exit must remain in the same 2024/2025 year.
    """
    n = len(source_df)
    out = np.full(n, np.nan, dtype=float)
    if n == 0 or len(raw_m1_df) == 0:
        return out

    raw_ns = _utc_ns(raw_m1_df.time)
    raw_open = raw_m1_df.open.to_numpy(dtype=float)
    source_ns = _utc_ns(source_df.time)
    nat = np.iinfo(np.int64).min

    entry_target = source_ns + int(tf_seconds * 1_000_000_000)
    exit_ts = source_df.time.shift(-(horizon + 1))
    exit_ns = _utc_ns(exit_ts)

    entry_idx = np.searchsorted(raw_ns, entry_target, side='left')
    safe_exit_target = np.where(exit_ns == nat, raw_ns[-1] + 1, exit_ns)
    exit_idx = np.searchsorted(raw_ns, safe_exit_target, side='left')

    good = (
        (exit_ns != nat)
        & (entry_idx < len(raw_ns))
        & (exit_idx < len(raw_ns))
        & np.isfinite(source_atr.to_numpy(dtype=float))
    )
    if not np.any(good):
        return out

    rows = np.flatnonzero(good)
    ent_i = entry_idx[rows]
    ex_i = exit_idx[rows]
    sig_year = source_df.time.dt.year.to_numpy()[rows]
    ent_year = pd.to_datetime(raw_ns[ent_i], unit='ns', utc=True).year.to_numpy()
    ex_year = pd.to_datetime(raw_ns[ex_i], unit='ns', utc=True).year.to_numpy()
    same_year = (sig_year == ent_year) & (ent_year == ex_year) & np.isin(sig_year, [2024, 2025])
    rows = rows[same_year]
    if len(rows) == 0:
        return out

    ent_i = entry_idx[rows]
    ex_i = exit_idx[rows]
    atrv = source_atr.to_numpy(dtype=float)[rows]
    out[rows] = direction * (raw_open[ex_i] - raw_open[ent_i]) / atrv
    return out


base.raw_m1_reference_return = raw_m1_reference_return

EDGE_DRIFT_LIMIT = base.EDGE_DRIFT_LIMIT
SELECTED_MISMATCH_LIMIT = base.SELECTED_MISMATCH_LIMIT
EXPECTED_R5_SHA256 = base.EXPECTED_R5_SHA256
source_row_return = base.source_row_return
mismatch_share = base.mismatch_share


def main() -> int:
    return base.main()


if __name__ == '__main__':
    raise SystemExit(main())
