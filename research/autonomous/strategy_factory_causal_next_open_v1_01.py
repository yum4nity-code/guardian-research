#!/usr/bin/env python3
from __future__ import annotations

"""Infrastructure-only repair wrapper for the frozen R5 causal next-open factory.

Scientific logic remains in strategy_factory_causal_next_open_v1_00. The only
change is to force the return vector to own writable memory before the existing
calendar-boundary mask assigns NaN. This repairs the NumPy/pandas read-only
array failure observed by preflight r1 without altering the frozen hypothesis,
features, thresholds, execution semantics, statistics, data windows, seed or
selection criteria.
"""

import numpy as np
import strategy_factory_causal_next_open_v1_00 as base


def causal_return(df, atr, h, direction):
    # Frozen R5 semantics: signal after close[t], entry open[t+1],
    # exit open[t+h+1]. copy=True is the sole infrastructure repair.
    ent = df.open.shift(-1)
    ex = df.open.shift(-(h + 1))
    ret = np.array(((ex - ent) / atr * direction).to_numpy(dtype=float), dtype=float, copy=True)
    signal_year = df.time.dt.year.to_numpy()
    entry_year = df.time.shift(-1).dt.year.to_numpy()
    exit_year = df.time.shift(-(h + 1)).dt.year.to_numpy()
    valid = (
        np.isfinite(ret)
        & (signal_year == entry_year)
        & (entry_year == exit_year)
        & np.isin(signal_year, [2024, 2025])
    )
    ret[~valid] = np.nan
    return ret


# Patch only the failing helper in the frozen implementation. All calls made by
# base.main() resolve this replacement through the base module global.
base.causal_return = causal_return


if __name__ == '__main__':
    raise SystemExit(base.main())
