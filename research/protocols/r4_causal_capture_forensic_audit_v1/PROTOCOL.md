# R4 causal-capture forensic audit v1

Status: preregistered descriptive audit only.

## Purpose

Explain the exact loss between the frozen R4 close-to-close statistical target and the later causal economic replay, without any new discovery, tuning, candidate elimination, 2026 access, or downstream queueing.

Known pre-audit observations to reproduce, not optimize around:

- 500/500 frozen R4 candidates had positive 2024 close-to-close selected mean.
- 500/500 were positive in a direct close-to-close 1 oz reconstruction for 2024.
- 252/500 were positive after first-available raw-M1 next-open mapping without overlap.
- 200/500 were positive after one-position-per-candidate overlap handling.
- 0/500 passed the frozen E1 economic screen in 2024.

These observations are descriptive facts from the completed screen and do not alter any rule.

## Immutable population and inputs

Population: exactly the 500 published R4 survivors in original array order.

Market inputs: exactly the four already-certified pre-2026 Phase I-B XAUUSD files and their existing SHA-256 pins:

- M1 raw
- M1 news-clean
- M5 raw
- M5 news-clean

R4 source artifact must match the existing pinned source hash.

No globbing, recursive discovery, read-then-filter, network market input, or protected-2026 file access is permitted.

## A. M5-to-M1 mapping audit

For every complete raw M5 bucket whose raw M1 timestamps t,t+60,t+120,t+180,t+240 all exist, verify:

- M5 open = first M1 open
- M5 high = max of five M1 highs
- M5 low = min of five M1 lows
- M5 close = last M1 close

Record complete buckets, incomplete buckets, exact matches, field mismatch counts, max absolute differences, and the twenty largest mismatches.

Apply the same descriptive check to retained M5 news-clean timestamps against raw M1. Separately confirm M5 news-clean retained OHLC equals M5 raw OHLC at the same timestamp.

Any non-trivial OHLC mismatch above numerical parse tolerance on complete buckets yields DATA_MAPPING_BLOCKED. Incomplete buckets are reported separately and do not count as mismatches.

## B. Exact B-to-C accounting

For every frozen candidate and every boundary-safe selected signal in 2024 and 2025:

B = direction * (source_close_exit - source_close_signal)

ENTRY_DELTA = direction * (source_close_signal - raw_M1_open_entry)

EXIT_DELTA = direction * (raw_M1_open_exit - source_close_exit)

C = direction * (raw_M1_open_exit - raw_M1_open_entry)

Entry reference is the first raw M1 open at or after signal-bar close.
Exit reference is the first raw M1 open at or after horizon-bar close.

Require the numerical identity:

C = B + ENTRY_DELTA + EXIT_DELTA

to machine tolerance for every audited event.

No costs and no overlap suppression are applied in this section.

## C. Attribution

Report ENTRY_DELTA and EXIT_DELTA separately by:

- 2024 / 2025
- M1 / M5
- raw / news-clean
- horizon 1/3/6/12/24/48
- direction long / short
- feature family ret / sma / rsi / body

For each group report count, sum, mean, median, P10, P25, P75, P90, P95, P99, adverse share and favorable share.

No group becomes a selection filter.

## D. Selected signal vs same-session complement

For each candidate, preserve the original R4 session/base mask.

Measure immediate post-close movement:

direction * (first_raw_M1_open_after_bar_close - source_close)

for selected bars and for the same-session complement.

Report selected mean, complement mean, and selected-minus-complement by candidate and aggregated descriptively.

This section is explanatory only. It performs no hypothesis search, ranking gate, or retuning.

## E. Overlap

Starting from causal no-overlap C, apply exactly the existing one-position-per-candidate replay semantics.

Report:

- total selected signals
- executable trades
- ignored overlap signals
- overlap rate
- no-overlap gross
- overlap-constrained gross
- OVERLAP_DELTA = D - C

No overlap rule changes are permitted.

## F. Existing frozen costs

On overlap-constrained trades only, apply exactly the already-frozen E1 and STRESS profiles from the economic screen.

Report gross, spread, slippage, commission, net, average specified cost per trade, gross expectancy per trade, gross/cost ratio, and descriptive break-even cost.

No new cost profile may be introduced.

## G. News-clean execution anomaly audit

For each overlap-constrained trade belonging to a news-clean candidate, check whether the raw-M1 entry and exit reference timestamps also exist in M1 news-clean.

Report absent-clean entry count/share, absent-clean exit count/share, any-anomaly count/share, and associated gross/E1-net sums.

Do not alter those trades in this audit.

## H. Invariants

The audit must confirm:

- exactly 500 candidate signatures, unchanged
- no candidate eliminated
- no new discovery
- no threshold/session/horizon/direction changes
- no 2026 market data opened
- no source artifact modified
- no next research phase queued by the audit itself
- exact B + ENTRY_DELTA + EXIT_DELTA = C accounting
- deterministic output for fixed inputs

## Verdict

The audit answers only:

1. Is the raw-M1 execution grid coherent with the M5 bars used by R4?
2. What exact share of B-to-C degradation comes from entry mapping?
3. What exact share comes from exit mapping?
4. Is immediate post-close movement systematically worse for selected signals than for the same-session complement?
5. How much additional degradation comes from overlap?
6. How much additional degradation comes from the already-frozen costs?
7. How often do news-clean strategies execute at M1 timestamps absent from the clean M1 set?
8. Is the completed 0/500 economic FAIL scientifically interpretable as executed, or is it DATA_MAPPING_BLOCKED?

Outputs: machine-readable JSON, candidate-level CSV, concise Markdown summary, progress JSON and provenance hashes.

No OOS, no live deployment, no new factory and no automatic downstream job are authorized by this protocol.
