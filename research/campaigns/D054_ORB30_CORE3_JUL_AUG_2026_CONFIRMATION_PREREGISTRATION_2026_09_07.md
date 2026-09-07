# D054 — ORB30 Core-3 — Jul-Aug 2026 Confirmation Preregistration

Date frozen: 2026-09-07 Europe/Paris
Status: **PREREGISTERED BEFORE ANY D054 HOLDOUT INSPECTION**
Parent evidence: D053-US-INDEX-ORB30-ENTRY-ALPHA-V0

## Scientific boundary

D053 is formally closed `D053_REJECT_V0` because its frozen month-block bootstrap lower 95% bound was not >0. D053 nevertheless produced a strong descriptive pattern on 2024-2025: SPX500, NDX100 and US30 were independently positive while US2000 was slightly negative.

D054 does **not** rewrite, rescue, waive, or recalculate D053. D054 is a new derived hypothesis whose market selection is explicitly informed by D053 and therefore must be judged only on data not used to choose that selection.

The untouched confirmation window is fixed at **2026-07-01 through 2026-08-31**, inclusive under the MT5 tester date contract. No D054 result from this window may be inspected before this document and the D054 runner/manifest identities are frozen.

## Frozen hypothesis

The exact D053 v1.01 ORB30 rule carries positive and temporally stable directional expectancy after costs on the three D053-positive US index CFDs:

- SPX500
- NDX100
- US30

No US2000. This exclusion is explicitly a D053-derived market-selection hypothesis, not an assertion that D053 itself passes without US2000.

## Frozen trading rule

Reuse the **unchanged D053 v1.01 source** and execution semantics:

- timeframe M15 tester, model 0 / Every tick;
- FundedNext server-time opening range: 16:30:00 through 16:59:59;
- from 17:00:00, first executable breakout only;
- long trigger = opening-range executable ASK high + 1 trade tick;
- short trigger = opening-range executable BID low - 1 trade tick;
- initial stop = opposite executable opening-range extreme;
- maximum one trade per symbol/day;
- no TP;
- no break-even;
- no trailing;
- no partial close;
- no trend, volatility, weekday, direction or width filter;
- nominal forced liquidation = first executable tick at/after 22:45 server time;
- if the broker session supplies no 22:45-or-later same-day tick, use the D053 v1.01 engineering fallback: last executable same-day tick, exit reason `SESSION_END`;
- executable ASK/BID prices;
- zero explicit index commission as in D053;
- frozen 1.5x executable-spread stress retained.

The canonical source is the already frozen D053 v1.01 file:
`research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5`

Normalized source SHA256 expected:
`d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad`

Git blob expected:
`7da58ecf8968d6814b634be0ee0043b9616fb6c6`

No source modification is permitted for D054.

## Frozen confirmation window

- from: 2026-07-01
- to: 2026-08-31
- symbols: SPX500, NDX100, US30
- execution: sequential, one MT5 run per symbol
- tester model: 0 / Every tick

## Frozen gates

D054 is **CONFIRMED** only if every gate below passes:

1. aggregate closed trades >= 100;
2. each symbol closed trades >= 25;
3. aggregate mean net R > 0;
4. aggregate PF >= 1.05;
5. aggregate total net R > 0;
6. 1.5x spread-stress aggregate total net R > 0;
7. at least 2 of 3 symbols have positive total net R;
8. July 2026 total net R > 0;
9. August 2026 total net R > 0;
10. LONG mean net R > 0;
11. SHORT mean net R > 0;
12. day-block bootstrap 95% lower bound of mean net R > 0, 20,000 deterministic resamples;
13. maximum positive-symbol contribution share <= 0.70;
14. integrity events = 0.

If any gate fails, verdict is `D054_UNCONFIRMED_CLOSE`.

No gate waiver, rounding rescue, alternate bootstrap, market deletion, direction deletion, date deletion, OR-width grid, time retune, stop retune, or management retune is allowed after seeing D054.

## Bootstrap definition

Blocks are UTC/broker-date `day_key` groups from the D054 trade evidence. For each bootstrap replicate, sample the observed unique day blocks with replacement, preserving all symbol trades inside each selected day block. Compute aggregate mean net R over the sampled rows. Use deterministic seed `540054` and 20,000 replicates. Gate uses the empirical 2.5th percentile and requires it to be strictly >0.

## D053 audit separation

A descriptive D053 audit may be generated from the already-seen 2024-2025 D053 trades to study month stability, rolling windows, weekdays, breakout latency, path, exit reasons and DST-alignment effects.

That audit is **diagnostic only**. D054 rules and gates in this document are frozen before that audit is inspected. No audit finding may modify D054.

## Decision consequences

If D054 confirms:
- preserve the exact ORB30 Core-3 signal as an entry-alpha baseline;
- begin prospective Sep-Dec 2026 tracking without retuning;
- any management experiment must be a separate preregistered layer and must compare against this unchanged baseline.

If D054 fails:
- close D054 without rescue;
- D053 remains an economically interesting but statistically unconfirmed historical signal;
- any later ORB variant must be a new hypothesis with a new untouched evidentiary boundary.
