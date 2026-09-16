# R31 — R6B FundedNext RAW vs NEWS-CLEAN ablation — 2026-09-16

## Question

Does the frozen +/-5 minute high-impact USD news exclusion materially create or
improve the economic edge of R6B-347 / R6B-307 on the exact same FundedNext
2024-2025 market feed?

## Inputs

Canonical Phase I-B:
- raw M1 SHA256 f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445
- raw M5 SHA256 ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66
- news-clean M5 SHA256 972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503
- Phase I-A merged mask SHA256 84da08ccad25fa0d4770110b24c774a075a01a3bf5fad2e90205c43e19604067
- 634 merged intervals
- 1,885 / 142,549 M5 rows excluded = 1.322352313941171%

## Frozen strategy rules

R6B-347:
- LONG
- lookback 96 M5
- buffer 0.10 ATR14
- UTC00_08
- horizon 96 M5 rows

R6B-307:
- LONG
- lookback 96 M5
- buffer 0.00 ATR14
- UTC00_08
- horizon 48 M5 rows

## Variants

RAW:
- raw FundedNext M5 for signal generation
- raw FundedNext M1 for execution

NEWS_CLEAN:
- exact Phase I-B news-clean FundedNext M5 for signal generation
- same raw FundedNext M1 for execution

No other change is permitted.

## Evaluation

Run 2024 and 2025 separately, matching original R6 year isolation.

Report for each candidate/year/variant/profile:
- trades
- net
- expectancy
- PF
- win rate
- max realized drawdown
- capital from 10,000 at 1x notional

Also report pooled 2024+2025 capital and deltas NEWS_CLEAN - RAW.

## Interpretation

This is an ablation diagnostic, not a new independent validation.

If NEWS_CLEAN materially improves both years for R6B-347, the news exclusion is
part of the effective strategy definition and R30 RAW cannot be treated as a
faithful long-history falsification of the original R6B strategy.

If RAW and NEWS_CLEAN are similar, the R30 long-history failure is more likely
a genuine regime/history issue.

No 2026 access. No parameter tuning. No live action.
