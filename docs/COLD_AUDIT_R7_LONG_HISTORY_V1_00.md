# R7 LONG-HISTORY CAUSAL FACTORY — COLD AUDIT v1.00

Date: 2026-09-12  
Scope: `r7_long_history_data_v1_00.py`, `r7_long_history_causal_factory_v1_00.py`, both R7 regression test files, and the frozen preregistration.

## Verdict

**PASS FOR PREFLIGHT EXECUTION ONLY.**

This verdict authorizes syntax/regression preflight and, if that preflight passes, the preregistered R7 data acquisition and research run. It is not a scientific PASS, not an EA promotion, and not authorization for live/real trading.

## Frozen research protocol

- Source universe: BTCUSDT and ETHUSDT spot only.
- Raw source: official Binance Data Vision monthly 5-minute klines.
- Raw window: 2017-08 through 2025-12 only.
- Search seed: 260912.
- Search size: 50,000 trials.
- Search timeframes: M15 and H1.
- Discovery: 2017-08-01 through 2022-12-31.
- Independent confirmation: 2023-01-01 through 2024-12-31.
- Pre-OOS temporal gate: calendar year 2025.
- 2026 remains forbidden/unopened.
- Survivors remain statistical alpha candidates and must later pass economic-cost, stress-cost, concentration, drawdown, rolling stability, redundancy and broker/MT5 fidelity filters.

## Cold-read findings found and repaired before execution

### 1. Critical inherited year guard

The first R7 draft reused the prior R5 `causal_return` helper. That helper explicitly authorized only years 2024 and 2025. Reusing it would have silently turned the intended 2017-2022 discovery returns into NaN.

Repair: R7 now owns a dedicated `causal_return` authorizing only 2017..2025 and explicitly rejecting cross-year holding paths. A regression test verifies a 2020 causal return is finite.

### 2. Missing-bar / resampling integrity

A simple OHLC resample could have synthesized an apparently valid M15/H1 candle from an incomplete 5-minute bucket, and path-dependent indicators could bridge a missing period as if the bars were adjacent.

Repair:
- M15 requires exactly 3 source 5m rows per bucket.
- H1 requires exactly 12 source 5m rows per bucket.
- incomplete buckets are dropped;
- feature/ATR computation resets at every resulting time gap;
- holding returns fail closed if any expected M15/H1 transition inside entry-to-exit is missing.

Synthetic tests cover both incomplete buckets and feature reset after a gap.

### 3. Duplicate timestamps

Earlier drafts sorted and deduplicated timestamps, which could hide source corruption.

Repair: monthly data, consolidated data and factory inputs now fail explicitly on duplicate timestamps. No silent deduplication is permitted.

### 4. Windows atomic progress writes

Prior research exposed transient Windows `os.replace` permission errors.

Repair: R7 progress/manifest atomic writes retry bounded PermissionError cases before failing. Other errors still fail closed.

### 5. Protected-period and selection leakage

Checked:
- data builder forbids an end month in 2026;
- factory rejects any input row >= 2026-01-01;
- rule thresholds are fit only on discovery data;
- discovery candidate IDs are frozen/hashes recorded before 2023-2024;
- confirmation survivors are frozen/hashes recorded before 2025;
- no rule, threshold, direction, timeframe, horizon or session is changed in 2025;
- adjacent-quantile robustness uses quantiles refit only on discovery values, then evaluated on confirmation;
- 2023/2024 confirmation applies HAC and BH-FDR across the frozen discovery candidates;
- 2025 applies a separate BH-FDR gate across the frozen confirmation survivors.

### 6. Execution timing / look-ahead

Checked:
- features at bar i use data available by bar-i close;
- signal is evaluated only after that close;
- earliest fill proxy is open[i+1];
- exit is open[i+h+1];
- ATR normalization comes from signal-time/past data;
- cross-calendar-year holding paths fail closed.

No bar-i close-to-next-open return is captured as tradable PnL.

### 7. Storage and provenance

- All bulk data is targeted to `D:\MT5_Backtests\Research\Data\R7_LongHistory`, not C:.
- Preregistered estimate: <= 1 GiB.
- Minimum free-space gate: 5 GiB.
- Observed D: free space before execution was about 348 GB.
- Cached archives are reused only if they are valid ZIP files; corrupted cache files are deleted and reacquired.
- Each downloaded archive and each consolidated CSV receives a local SHA-256 recorded in the manifest.
- Timestamp-unit parsing supports seconds/milliseconds/microseconds by magnitude.
- Source gaps are recorded rather than filled or invented.

A network/source 404, malformed archive, or inadequate history is an infrastructure/data failure, not a scientific FAIL.

## Statistical interpretation

The discovery p-value is intentionally only a screening statistic. Scientific confirmation is independent in time and uses HAC plus BH-FDR after the discovery set is frozen. The later 2025 gate is a second, frozen temporal gate.

This design does **not** claim realistic trading profitability yet. R7 v1.00 has no broker-specific spread/commission/slippage replay in the search stage. Economic viability is a mandatory downstream filter on survivors only.

## Regression preflight required before main execution

The following must pass locally on Windows from the current deployed main commit:

1. Python `py_compile` for both R7 executors and both R7 tests.
2. `test_r7_long_history_data_v1_00.py`.
3. `test_r7_long_history_causal_factory_v1_00.py`.
4. Confirm the deployed preregistration matches main and 2026 remains unopened.

Only after all four pass may the R7 downloader run. Only after the downloader produces a valid manifest may the 50,000-trial factory run.

## Residual risks

- Official archive availability is not assumed; missing months fail closed.
- Real exchange downtime can create gaps; R7 does not invent missing bars and resets path-dependent features across them.
- Binance spot history is a research data source, not a guarantee of prop-firm execution parity.
- BTC and ETH are the first long-history batch, not the final intended multi-asset universe.
- Any R7 survivor still requires the preregistered post-survivor filters before MT5 fidelity work.

**Cold-audit status: PASS FOR PREFLIGHT EXECUTION ONLY.**
