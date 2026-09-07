# D054 — ORB30 Core-3 Jul-Aug 2026 Confirmation — Closeout

Date: 2026-09-07 Europe/Paris
Experiment: `D054-ORB30-CORE3-JUL-AUG2026-CONFIRMATION-V0`
Final status: **D054_UNCONFIRMED_CLOSE**

## Scientific boundary

D054 was a new D053-derived hypothesis, not a rescue or rewrite of D053. The Core-3 universe SPX500 / NDX100 / US30 was chosen from already-seen D053 2024-2025 discovery evidence and then evaluated only on untouched Jul-Aug 2026.

The exact D053 v1.01 source was reused unchanged:
`research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5`

Normalized source SHA256:
`d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad`

No post-hoc market, direction, timing, stop, management, threshold, date or bootstrap rescue is permitted.

## Authoritative result

Event:
`backtests/d054/live/events/confirmation/d054-confirmation-score/20260907T182809Z`

Confirmation window:
- 2026-07-01 through 2026-08-31
- SPX500, NDX100, US30
- Model 0 / Every tick
- integrity events: 0

Aggregate:
- n: **127**
- mean net R: **-0.199334R/trade**
- PF: **0.559651**
- total net R: **-25.315464R**
- 1.5x spread-stress total: **-26.342194R**

Per symbol:
- SPX500: 43 trades, **-6.053875R**
- NDX100: 42 trades, **-9.204839R**
- US30: 42 trades, **-10.056750R**
- positive symbols: **0/3**

By month:
- July 2026: **-18.952060R**
- August 2026: **-6.363405R**

By direction:
- LONG: 61 trades, mean **-0.198853R**, total **-12.130049R**
- SHORT: 66 trades, mean **-0.199779R**, total **-13.185416R**

Day-block bootstrap, 20,000 deterministic resamples:
- lower 95%: **-0.368529R/trade**
- median: **-0.200567R/trade**
- upper 95%: **-0.017671R/trade**

The entire bootstrap interval is below zero.

## Gate verdict

Passed only engineering/count/concentration gates. Failed the economic/robustness gates:
- aggregate mean >0
- PF >=1.05
- aggregate total >0
- spread-stress total >0
- positive-symbol minimum
- July positive
- August positive
- LONG mean positive
- SHORT mean positive
- day-block bootstrap lower 95% >0

Formal verdict: **D054_UNCONFIRMED_CLOSE**.

## Interpretation

This is materially different from D053. D053 was economically strong in 2024-2025 but failed one temporal-robustness gate. D054 then tested the D053-derived Core-3 hypothesis on untouched Jul-Aug 2026 and found a broad negative result: all three indices negative, both months negative, both directions negative, PF well below 1, stress negative, and even the bootstrap upper 95% bound below zero.

Therefore the exact D053/D054 ORB30 baseline is **not confirmed as a persistent entry-alpha engine** and must not be promoted to production.

The D053 descriptive audit remains useful for generating future hypotheses, but no filter discovered there may be applied retrospectively to Jul-Aug 2026 and called confirmation. Any further ORB hypothesis must be separately preregistered and evaluated on a new untouched boundary, preferably prospectively from dates after this D054 result.

## Next research boundary

Do not run another Jul-Aug 2026 ORB variant after seeing D054.

A future D055 may use the already-seen D053/D054 evidence only as hypothesis-generation material and must freeze its rule before evaluating new unseen data. Candidate future work can include session-clock alignment, breakout-latency structure or regime/context hypotheses, but only with a new evidence boundary.
