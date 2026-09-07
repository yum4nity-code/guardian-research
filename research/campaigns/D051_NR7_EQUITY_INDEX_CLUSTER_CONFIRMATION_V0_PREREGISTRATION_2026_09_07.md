# D051 — NR7 Equity-Index Cluster Confirmation V0 — Preregistration

Date frozen: 2026-09-07 Europe/Paris
Status: **PREREGISTERED BEFORE ANY D051 2026 INDEX OUTCOME INSPECTION**

## Scientific role

D051 is a **new subgroup hypothesis** generated from the closed Market Transport Lab V1. It is not a rescue or relabeling of D038 or D047.

The parent D038 NR7 V0 verdict remains `REJECT_V0` because its original frozen count gate failed. D047 Market Transport V1 remains `TRANSPORT_NO_BROAD_PASS` because the frozen 12-market transport universe failed broad development gates.

D051 asks a narrower, coherent asset-class question on untouched future data.

## Discovery that generated the hypothesis

In D047 2024-2025 development, all four equity-index CFDs were positive under the unchanged NR7 transport source:

- SPX500: n=76, +6.36985704R
- NDX100: n=67, +8.17337784R
- GER30: n=78, +13.42649242R
- US30: n=78, +3.69906988R

Combined discovery-only index cluster:

- n = 299
- total = +31.66879718R
- mean = +0.10591571R/trade
- 4/4 indices positive

These values were observed after opening 2024-2025 development and are therefore **not confirmation evidence**.

## Frozen hypothesis

> The unchanged D038/D047 NR7 volatility-contraction breakout has a positive, distributed edge across the FundedNext equity-index cluster SPX500, NDX100, GER30 and US30, distinct from its failed broad 12-market transport result.

## Frozen markets

Exactly four symbols:

- SPX500
- NDX100
- GER30
- US30

No symbol may be removed, added or substituted after D051 confirmation outcomes are inspected.

## Strategy semantics — exact freeze

D051 preserves the D038/D047 strategy semantics:

- previous completed broker D1 bar must be strict NR7: smallest positive range among D-1 through D-7;
- next broker day: first executable tick break of NR7 high/low wins;
- long entry at observed ASK; short entry at observed BID;
- stop at opposite NR7 extreme;
- maximum one trade per setup/day; no reversal;
- no TP, trailing, BE, partial, RSI, EMA, ATR regime, trend filter, weekday filter, news filter or parameter search;
- exit at stop, last executable tick before broker-day change, or tester end;
- native executable-side Trade Path retained.

D051 uses the same deterministic Market Transport V1 index handling as D047:

- tester spread retained through executable BID/ASK;
- zero explicit index commission in the parent-comparable transport model;
- USD account;
- Model=0 / Every Tick;
- sequential MT5 only.

The executable source may differ from D047 only in evidence identity/name/version needed to isolate D051. No signal, exit, risk, timing, market-class or cost semantics may change.

## Prior engineering proof

All four D051 symbols already completed D047 2024-2025 Model0 runs with clean lifecycle/integrity under the same strategy and transport semantics. Therefore D051 does not require a new profitability-free smoke run merely to re-prove the exact same symbol/source mechanics.

The D051 command must still compile the deterministic D051 evidence-identity derivative before running confirmation.

## Frozen confirmation window

First untouched D051 confirmation:

- from: 2026-01-02
- to: 2026-06-30
- symbols: SPX500, NDX100, GER30, US30
- Model=0 / Every Tick

No D051 NR7 index result from this period had been inspected when this preregistration was frozen.

## Frozen confirmation gates

All must pass:

1. aggregate n >= 60;
2. each of the four symbols n >= 10;
3. aggregate mean net R > 0;
4. aggregate PF >= 1.10;
5. at least 3/4 symbols have positive total net R;
6. aggregate total net R > 0;
7. no single positive symbol contributes more than 60% of total positive-symbol R;
8. integrity events = 0.

Because the frozen Market Transport index cost model has zero explicit commission, a 1.5x explicit-commission stress is numerically identical and is not used as a separate discriminating gate. Executable tester spread remains present.

### Pass

`D051_CONFIRM_PASS_OPEN_RESERVED_HOLDOUT`

A pass does not yet authorize Guardian production integration. It only authorizes opening the already-reserved final holdout below with unchanged rules.

### Fail

`D051_UNCONFIRMED_CLOSE`

On failure:

- no symbol removal;
- no index-by-index rescue;
- no threshold/lookback/stop/exit retuning on the opened H1 sample;
- no replacement with XAGUSD or another discovered winner;
- D051 closes.

## Reserved final holdout — locked now

If and only if every H1 confirmation gate passes, a final holdout is reserved now before H1 inspection:

- 2026-07-01 through 2026-08-31
- same four symbols
- same exact source semantics and cost model

Frozen final-holdout gates:

1. aggregate n >= 20;
2. aggregate mean net R > 0;
3. aggregate PF >= 1.05;
4. at least 2/4 symbols positive;
5. aggregate total net R > 0;
6. integrity events = 0.

The reserved holdout must not be inspected if H1 confirmation fails.

## Interpretation boundary

D051 is deliberately asset-class coherent: **all four equity indices are kept**. It does not cherry-pick only the best D047 index.

A D051 pass would support a new NR7-index candidate lineage. It would not retroactively change D038 `REJECT_V0` or D047 `TRANSPORT_NO_BROAD_PASS`.
