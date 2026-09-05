# D035 analyzer runtime compatibility fix — 2026-09-05

Status: **IMPLEMENTATION FIX / NO SCIENTIFIC RULE CHANGE**

Observed on the user's Windows Python 3.13 / pandas runtime after Binance BTCUSDT OI metrics and 1m klines loaded:

`pandas.errors.MergeError: incompatible merge keys datetime64[ms, UTC] and datetime64[us, UTC]`

Root cause: pandas preserved different datetime resolutions for the two Binance archive paths. `merge_asof` requires identical key dtypes even though the timestamps represent the same UTC instants.

Correction in analyzer v1.01: normalize both `left['ts']` and metrics `m['ts']` explicitly to `datetime64[ns, UTC]` before sorting and `merge_asof`.

Frozen D035 research design is unchanged: no shock percentile, rolling window, cooldown, merge window, target rule, response horizon, gate, cost treatment, or 2026 untouched holdout boundary was modified.

Regression QA performed before user delivery:
- Python syntax compile: PASS.
- Synthetic reproduction with kline index `datetime64[ms, UTC]` and OI index `datetime64[us, UTC]`: PASS after normalization.
- No MT5 CFD export/backtest rerun is required.
- Existing `D035_binance_cache` should be retained so already-downloaded Binance files are reused.

Exact source diff is archived at `research/analysis/D035_Binance_Deleveraging_LeadLag_v1_00_to_v1_01.patch`.
