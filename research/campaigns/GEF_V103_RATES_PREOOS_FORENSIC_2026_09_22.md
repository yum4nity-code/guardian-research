# GEF V103 — Final pre-OOS forensic for V102 standalone rates

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Frozen source

V102 completed:
- run_id: GEF102-20260922-143744
- engine: V102.0
- finite rate tests: 10902
- discovery frozen: 200
- replication survivors: 34
- robustness survivors: 27
- validation survivors: 5
- final survivors SHA256: f6aa7d91488a5e52eeb1d5fa3c614dcff918ac3f1e4dd680ec3e3cac7060b865
- 2023-2025 accessed: false
- 2026 accessed: false

V103 may only audit those exact five V102 survivors. No replacement, rescue, retuning or new candidate selection.

## The five frozen candidates

1. rates_yields_NOM_BC_1MONTH_level | HI | USDJPY_fwd_240m | SHORT
2. rates_yields_REAL_TC_7YEAR_d1 | LO | GBPUSD_fwd_120m | LONG
3. rates_yields_REAL_TC_7YEAR_d1 | LO | AUDUSD_fwd_120m | LONG
4. rates_yields_REAL_TC_7YEAR_d1 | LO | EURUSD_fwd_120m | LONG
5. rates_yields_NOM_BC_3MONTH_d5 | HI | USDCHF_fwd_120m | SHORT

The three REAL_TC_7YEAR_d1 candidates share one signal definition and must be treated as one economic signal family for independence counting, even though each target is audited individually.

## Audit window

Use only <= 2022 data.

Primary forensic window: frozen validation 2018-2022.
Earlier data may be used only to reconstruct causal state history.

Forbidden:
- 2023-2025
- 2026+

## Mandatory exact-source checks

- locate exact V102 run GEF102-20260922-143744;
- verify status COMPLETE_V102_STANDALONE_RATES;
- verify FINAL_SURVIVORS.csv SHA256 equals f6aa7d91488a5e52eeb1d5fa3c614dcff918ac3f1e4dd680ec3e3cac7060b865;
- verify exactly 5 rows;
- use canonical V83B anchoring and V102 state semantics.

## Candidate-level forensic

For every candidate on 2018-2022:

Baseline:
- N
- mean bp
- median bp
- win rate
- yearly means

Concentration:
- trim best 1%
- trim best 2%
- trim best 5%
- remove best 5 events
- remove best 10 events
- remove best calendar month, where "best" is the month with the largest total directional contribution
- leave-one-year-out minimum mean

Dependence / repeated-regime stress:
- non-overlapping horizon events
- first eligible signal per UTC calendar day
- first eligible signal per contiguous TRUE state episode

Timing robustness:
- information delay +1 day
- information delay +2 days
- z threshold 0.9
- z threshold 1.1

Cost diagnostics:
- net after 1 bp
- net after 2 bp
- net after 3 bp
- net after 5 bp

Uncertainty:
- deterministic month-block bootstrap, 2000 draws, seed 103
- report 2.5%, 50%, 97.5% mean-bp quantiles

## Candidate final pre-OOS gate

A candidate passes V103 only if all are true:

- baseline mean > 0
- net after 1 bp > 0
- trim best 2% > 0
- trim best 5% > 0
- remove best 10 events > 0
- remove best calendar month > 0
- leave-one-year-out minimum > 0
- non-overlap mean > 0
- daily-first mean > 0
- state-episode-first mean > 0
- +1d lag mean > 0
- +2d lag mean > 0
- z0.9 mean > 0
- z1.1 mean > 0
- month-block bootstrap 2.5% lower bound > 0

Costs above 1 bp are diagnostics, not gates.

No gate may be relaxed after results are seen.

## Dependency audit

For all five candidates:
- compute exact signal-mask overlap / Jaccard on 2018-2022;
- compute directional return correlation on common signal timestamps where possible;
- define a signal-family key = feature + state + horizon + direction.

Candidates with the same signal-family key are not independent discoveries.

Report:
- candidate survivors;
- unique signal families among survivors;
- correlation matrix;
- signal-overlap matrix.

No portfolio optimization in V103.

## Stop rule

Regardless of result:
STOP after V103.
Do not open 2023-2025.
Do not open 2026.

A passing V103 result permits only a human decision about whether to create a separately frozen V104 locked-OOS protocol.
