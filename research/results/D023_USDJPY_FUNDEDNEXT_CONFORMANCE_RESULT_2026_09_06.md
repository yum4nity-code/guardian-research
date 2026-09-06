# D023 USDJPY London ORB — FundedNext conformance result

Date: 2026-09-06

## Status

**CANDIDATE — NOT VALIDATED**

This result is from the already-inspected 2024-2026 development/conformance period. It is not untouched confirmation.

## Engine

Reference source:

`research/strategies/d023/D023_USDJPY_LondonORB_M15_v1_04_FUNDEDNEXT_REFERENCE_20260906.mq5`

This source was the FundedNext/DST-aware diagnostic that produced the observed run output.

Frozen entry/exit semantics:

- USDJPY M15;
- London opening range 08:00-09:00;
- first M15 close outside range during 09:00-11:00 London;
- enter at next M15 open using executable-side spread convention;
- stop at opposite edge of OR;
- max one signal/day;
- stop or 16:00 London exit;
- no EMA/RSI/ATR/news/day/direction rescue filter.

## FundedNext conformance assumptions in this run

- FundedNext server clock modeled GMT+2 winter / GMT+3 US-DST period;
- London clock modeled UTC winter / UTC+1 BST period;
- US-vs-UK DST mismatch weeks handled explicitly;
- FundedNext Stellar 1-Step/2-Step Forex commission modeled as USD 5 per lot per side;
- observed historical spread embedded in executable prices.

## Observed result

Requested tester period: 2024-01-02 through 2026-06-26.

Observed trade rows: **482**.

Main metrics:

- mean net expectancy: **+0.0915R/trade**;
- cumulative net: **+44.10R**;
- net Profit Factor: **~1.176**;
- net win rate: **~41.7%**.

Year slices:

- 2024: **~+0.153R/trade**;
- 2025: **~+0.055R/trade**;
- 2026 first half: **~+0.034R/trade**.

The edge therefore remained positive in all three inspected calendar slices but weakened materially through time.

Cost stress:

- with commission multiplied by 1.5, pooled expectancy remained approximately **+0.059R/trade**;
- 2026 first-half expectancy became slightly negative, approximately **-0.007R/trade**.

Post-hoc side observation:

- LONG roughly **+0.134R/trade**;
- SHORT roughly **+0.043R/trade**.

This MUST NOT be converted into a LONG-only rule without independent validation.

## Statistical interpretation

This is enough evidence to continue the hypothesis, but not enough to promote it.

The time-block/bootstrap evidence was not strong enough to treat the development period itself as conclusive, and temporal decay is visible.

The correct next scientific action is the preregistered 2023 confirmation after the harness is proven reliable.

## Frozen 2023 pass gates

Declared before inspecting 2023:

- n >= 150;
- mean net R > 0;
- net PF >= 1.10;
- time-aware / 5-day moving-block bootstrap target lower bound > 0;
- total net R remains positive under 1.5x commission stress.

Do not alter these gates after seeing the 2023 result.

## Harness warning

Subsequent attempts to instrument the 2023 confirmation produced output-path / CSV-observability problems. The latest generated v1.07 harness was **not compile-validated** and must not be treated as authoritative.

Before requesting another full 2023 run:

1. audit the harness source;
2. compile for real;
3. smoke-test a short 2023 interval;
4. prove INIT stats output and exact file path;
5. inspect several trade rows manually;
6. only then run the full untouched confirmation.
