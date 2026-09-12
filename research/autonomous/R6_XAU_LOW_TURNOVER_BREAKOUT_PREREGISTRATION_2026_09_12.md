# R6 XAU low-turnover breakout — preregistration — 2026-09-12

## Why this family exists

R5 causal next-open discovery/confirmation produced 96 frozen gross survivors, but the frozen pre-OOS economic screen returned 0/96 under the inherited E1/STRESS cost gates. R5 is therefore closed as a tradable alpha family; it will not be retuned or rescued on the same samples.

R6 is a genuinely independent, structured event family. It does not reuse R5 one-feature tail rules, R5 thresholds, R5 survivor identities, or R5 random search. It asks whether comparatively infrequent rolling-range breakouts in XAUUSD generate sufficiently large post-signal moves to survive realistic first-available execution and costs.

## Data boundary

Only canonical Phase I-B 2024/2025 files are permitted:
- signal source: `xauusd_m5_2024_2025_news_clean.csv`, SHA256 `972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503`
- execution reference: `xauusd_m1_2024_2025_raw.csv`, SHA256 `f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445`

Any hash mismatch is an infrastructure FAIL. Any row timestamp >= 2026-01-01 is a hard FAIL. Protected 2026 must not be opened, listed as market data, or inspected.

## Causal event definition

M5 bar timestamps are treated as bar-open timestamps. A signal is known only after bar t completes. Entry is the first raw-M1 open at or after the end of bar t. Exit is the first raw-M1 open at or after the frozen source horizon endpoint. Cross-year trades are purged. Only one position may be open; overlapping signals are ignored chronologically.

For each M5 bar t, using only bars strictly before t:
- rolling high = max(high[t-L : t])
- rolling low = min(low[t-L : t])
- ATR14 is computed causally through t
- long event: close[t] > rolling_high + buffer_ATR * ATR14[t]
- short event: close[t] < rolling_low - buffer_ATR * ATR14[t]

No feature quantile is fitted. No R5 feature/threshold is reused.

## Frozen deterministic grid

- lookback bars L: 12, 24, 48, 96
- breakout buffer in ATR: 0.00, 0.10, 0.20
- holding horizon bars: 12, 24, 48, 96
- direction: long, short
- UTC signal session: ALL, 00-08, 08-16, 16-24

Total frozen grid: 384 candidate definitions.

## Costs

Use exactly the inherited R5 economic profiles, per unit of XAU:
- E1: commission rate 0.000007, spread 0.0002, slippage per side 0.0001
- STRESS: commission rate 0.000014, spread 0.0005, slippage per side 0.0002

The same deterministic cost formula and first-available raw-M1 execution semantics used by the R5 economic screen are reused for comparability. This is not a change to R5 and cannot rescue it.

## Development and confirmation

2024 is discovery only. A candidate advances to confirmation only if, on chronological non-overlapping trades:
- at least 30 executable 2024 trades
- E1 net > 0
- STRESS net > 0
- E1 net excluding the best positive trade > 0
- E1 profit factor > 1.0

2025 is untouched until the 2024 discovery set is frozen in memory. For each discovery candidate require:
- at least 30 executable 2025 trades
- at least 12 trades in each 2025 half
- E1 net > 0 in full 2025, H1 and H2
- STRESS net > 0 in full 2025, H1 and H2
- E1 full-year net excluding the best positive trade > 0
- E1 profit factor > 1.0

For confirmation significance, perform a deterministic day-block bootstrap of E1 trade net PnL in 2025 with 2,000 resamples and a candidate-specific seed derived from its frozen ID. The one-sided p-value is `(1 + count(bootstrap_mean <= 0)) / (B + 1)`. Apply Benjamini-Hochberg FDR across all 2024 discovery candidates and require q <= 0.05. Also require the bootstrap 5th percentile of mean trade net PnL > 0.

## Interpretation

PASS means one or more low-turnover breakout definitions survived causal execution, inherited transaction costs, chronological overlap handling, 2024 discovery, untouched 2025 confirmation, half-year stability, concentration rejection and multiplicity control. PASS is not an EA and does not authorize protected 2026.

FAIL closes this exact R6 rolling-range-breakout family. Do not retune it on 2025 and do not open 2026 to rescue it.

## Preflight gate

Before the market-data run, deterministic tests must verify at minimum:
- rolling breakout references only prior bars
- session masks
- inherited cost formula identity
- chronological one-position replay and cross-year purge on synthetic data
- Benjamini-Hochberg implementation
- deterministic block-bootstrap behavior
- protected-date rejection helper

The expensive/data-bearing job may run only after this preflight passes.