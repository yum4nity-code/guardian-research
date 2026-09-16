# R34 — Signal-feed × execution-feed factorial diagnostic

## Status and purpose

This document preregisters R34 before any R34 result is produced. R34 is a causal diagnostic of the FundedNext/Dukascopy divergence already observed in R31–R33. It is not a strategy search, validation, promotion, or tuning exercise.

## Frozen scope

- Candidate: `R6B-347` only.
- Rule: long; M5 close above `prior_96_high + 0.1 * ATR14`; signal hours `[00:00, 08:00)` in the corrected FundedNext server coordinate; entry at the first M1 open at or after signal-bar close; exit availability after 96 further M5 bars, using the first M1 open at or after that timestamp.
- Years: 2024 and 2025 only, evaluated separately and pooled only after both yearly cells exist.
- FundedNext inputs: the pinned Phase I-B RAW M5 signal file and RAW M1 execution file used by R31.
- Dukascopy inputs: the pinned R30 BID M5 and M1 yearly files, transformed with the R33 UTC→synthetic FundedNext server clock (`UTC+3` during New York DST, otherwise `UTC+2`).
- Cost profiles: unchanged existing `E1` and `STRESS` implementations.
- No 2026 data, news-clean variant, parameter tuning, leverage search, or alternative matching rule.

The exact frozen rule is:

```text
candidate_id=R6B-347
lookback_bars=96
buffer_atr=0.1
horizon_bars=96
session_start=0
session_end=8
direction=1
```

## Factorial intervention

Signal and execution feeds are varied independently:

| Cell | Signal computation | Entry/exit opens and costs |
|---|---|---|
| `FN_SIGNAL__FN_EXECUTION` | FundedNext RAW M5 | FundedNext RAW M1 |
| `FN_SIGNAL__DUKA_EXECUTION` | FundedNext RAW M5 | corrected-clock Dukascopy BID M1 |
| `DUKA_SIGNAL__FN_EXECUTION` | corrected-clock Dukascopy BID M5 | FundedNext RAW M1 |
| `DUKA_SIGNAL__DUKA_EXECUTION` | corrected-clock Dukascopy BID M5 | corrected-clock Dukascopy BID M1 |

The signal feed alone fixes signal timestamps and exit-availability timestamps. The execution feed alone supplies entry and exit prices at the first available M1 timestamp and therefore supplies the inputs to the unchanged cost engine. Missing execution references are counted, never imputed. The validated `top2.replay_window`, R6 ATR/signal functions, R33 clock transform, and economic cost/statistics engine are reused.

## Signal comparison

For every raw R6B-347 signal, export timestamp, close, high, ATR14, prior-96 high, and breakout threshold. Matching is deterministic and one-to-one:

1. exact timestamps are paired first;
2. unmatched signals are paired within ±5 minutes by smallest absolute distance, then earlier FN timestamp, then earlier Dukascopy timestamp;
3. remaining signals are paired within ±10 minutes by the same ordering.

Counts reported are exact, cumulative within ±5, cumulative within ±10, FN-only after ±10, and Duka-only after ±10. For each pair, export signed `Duka - FN` differences for close, high, ATR, prior-96 high, and threshold, plus absolute summaries. No price rescaling or tolerance fitting is allowed.

## Measurements and classification

Each cell reports accounting, E1/STRESS trade metrics, capital, and an auditable trade ledger for 2024 and 2025. Classification uses E1 yearly values for trades, net, expectancy_bps, and bounded PF. Finite non-negative PF is transformed to `PF / (1 + PF)`; the existing engine's `PF=null` (no gross loss) is treated as the bounded limit `1.0`. For each metric/year, the absolute signal main effect is the mean of the two execution-conditional signal-feed contrasts; the execution main effect is the mean of the two signal-conditional execution-feed contrasts. Each contrast is divided by the largest absolute value among its compared cells (floor `1e-12`). The median normalized contrast is the score for each axis.

- `SIGNAL_FEED_DOMINANT` if signal score is at least 2× execution score.
- `EXECUTION_FEED_DOMINANT` if execution score is at least 2× signal score.
- otherwise `MIXED`.
- if both scores are zero, classification is `MIXED`.

This classification rule is frozen before execution and must not be changed after results are seen.

## Required guards and outputs

The run must fail closed on input hash/provenance mismatch, unexpected years, any underlying timestamp at or after `2026-01-01T00:00:00Z`, changed R6B-347 constants, an existing output directory, or a missing matrix cell. Dukascopy server-year construction must load the previous and current UTC years before clock conversion so the first server hours are retained exactly as in R33. Outputs are staged in a sibling directory and the complete directory is renamed into place only after every artifact succeeds. Outputs are a result JSON, matrix-year CSV, signal-pair CSV (including explicit FN-only/Duka-only rows), per-feed signal CSV files, and four per-cell trade-ledger CSV files. A successful program exit means execution completed; it does not mean the strategy or either feed passed an alpha gate.
