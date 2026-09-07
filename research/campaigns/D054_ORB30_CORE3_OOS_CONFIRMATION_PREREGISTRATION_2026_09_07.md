# D054 — ORB30 Core-3 OOS Confirmation — Preregistration

Date frozen: 2026-09-07 Europe/Paris
Status: **FROZEN BEFORE D054 HOLDOUT INSPECTION**

## Purpose

D053 tested one fixed 30-minute FundedNext server-time opening-range breakout on SPX500, NDX100, US30 and US2000 over 2024-2025. D053 was formally rejected because one preregistered robustness gate failed: the month-block bootstrap lower 95% bound was <= 0. D053 nevertheless showed positive net expectancy, PF > 1.10, positive 1.5x spread stress, positive 2024 and 2025, positive LONG and SHORT subsets, and three positive markets. The three positive markets were SPX500, NDX100 and US30; US2000 was slightly negative.

D054 is a **new derived hypothesis**, not a rescue or reinterpretation of D053. The Core-3 universe is selected explicitly because D053 observed those three markets as positive. That selection is therefore in-sample/model-development information and must earn independent support on data not previously inspected by Guardian research.

D053's verdict remains `D053_REJECT_V0` regardless of D054.

## Frozen hypothesis

The unchanged D053 v1.01 ORB30 rule has positive and temporally robust out-of-sample expectancy after executable spread and frozen 1.5x spread stress on the derived Core-3 US-index cluster:

- SPX500
- NDX100
- US30

## Frozen strategy semantics

D054 reuses the exact D053 v1.01 executable strategy source and semantics. No signal parameter is changed.

- timeframe: M15 tester harness with tick execution (`Model=0`)
- opening range: FundedNext server time 16:30:00 through 16:59:59
- entry eligibility starts at 17:00:00 server time
- first breakout only, one trade maximum per broker day
- LONG trigger: opening-range executable ASK high + 1 trade tick
- SHORT trigger: opening-range executable BID low - 1 trade tick
- initial stop: opposite executable opening-range boundary
- no TP
- no breakeven
- no trailing
- no partial close
- no volatility, trend, weekday, width, news, direction or other filter
- nominal liquidation: first executable tick at/after 22:45 server time
- v1.01 engineering fallback: if the session has no executable tick at/after 22:45 before broker-day change, close at the final executable tick of that same broker day (`SESSION_END`)
- no overnight carry by design

The D053 source may still contain US2000 in its internal allowlist. D054's runner and manifest freeze the executed universe to Core-3 only. US2000 must not be run, scored, or substituted in D054.

## Source lineage frozen for D054

Parent source:
`research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5`

Required normalized SHA256:
`d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad`

Source version reported by the harness: `1.01`.

D054 is deliberately a source-reuse experiment: changing the source code after this preregistration is not allowed. Only a new experiment may change OR length, alignment, entry trigger, stop, exit or filters.

## OOS boundary

Frozen untouched confirmation window:

- from: **2026-07-01**
- to: **2026-08-31**
- symbols: **SPX500, NDX100, US30**

Guardian research must not inspect D054 economics from this window before this preregistration and runner contract are frozen.

There is no D054 tuning stage. The 2024-2025 D053 result is the development evidence that generated the Core-3 hypothesis; July-August 2026 is the first D054 decision window.

## Frozen cost model

Same as D053:

- executable ASK/BID entry and liquidation prices from Strategy Tester ticks
- explicit index commission: 0 in this benchmark, consistent with the D053 FundedNext index treatment
- primary net R uses executable spread already embedded in entry/exit prices
- stress R adds the frozen D053 adverse spread stress equivalent to 1.5x observed round-trip spread penalty relative to mid
- swap excluded because normal lifecycle is intraday / same broker day

## Frozen confirmation gates

D054 confirms only if **every** gate passes:

1. aggregate closed trades >= **120**
2. each Core-3 symbol closed trades >= **35**
3. aggregate mean net R > **0**
4. aggregate PF >= **1.05**
5. aggregate total net R > **0**
6. 1.5x spread-stress total net R > **0**
7. positive symbols >= **2 of 3**
8. July 2026 total net R > **0**
9. August 2026 total net R > **0**
10. LONG mean net R > **0**
11. SHORT mean net R > **0**
12. day-block bootstrap 95% lower bound of mean net R > **0**
13. maximum positive-symbol contribution share <= **0.65**
14. integrity events = **0**

Bootstrap:
- deterministic seed: `540054`
- 20,000 replications
- block = broker day across all Core-3 observations on that day, preserving same-day cross-market dependence
- statistic = aggregate mean net R per trade

The gates intentionally target the weakness observed in D053: temporal robustness. A merely positive total is insufficient.

## Decision policy

If every gate passes:
`D054_CONFIRMED_CORE3_OOS`

If engineering/integrity is valid but any economic/statistical gate fails:
`D054_UNCONFIRMED_CORE3_OOS`

If lifecycle/source/evidence integrity fails:
`D054_ENGINEERING_INCOMPLETE`

No waiver, rounding rescue, market deletion, direction deletion, OR-window change, exit retune, gate retune or second look at July-August 2026 is permitted after result inspection.

## D053 diagnostic audit boundary

A descriptive D053 audit may be run on the already-seen 2024-2025 trades to understand monthly instability, rolling performance, weekday, breakout timing, opening-range width, exit reason, path telemetry and US/EU DST-mismatch calendar windows.

That audit:
- cannot alter D054 rules, universe, dates or gates;
- cannot be used to filter D054 after the fact;
- cannot change D053's formal verdict;
- must be labelled descriptive / hypothesis-generating only.

## If D054 confirms

Only after confirmation may Guardian open a separate forward/production-readiness program. Candidate future work includes prospective Sep-Dec 2026 monitoring and a separately preregistered ORB management lab. D054 itself tests entry/context alpha only.
