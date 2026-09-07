# D044 — Turtle Soup 20-Day Failed-Break Reversal V0

Date frozen: 2026-09-07 Europe/Paris
Status: **PREREGISTERED / NO D044 MT5 OUTCOME SEEN**

## Scientific role

D044 is an **entry-alpha transport experiment** for the classic Turtle Soup failed-break concept associated with Linda Bradford Raschke and Laurence A. Connors, not a claimed full replication of the discretionary source management.

The source descriptions consistently specify the core setup as: a new 20-period extreme, the previous 20-period extreme old enough to matter, re-entry several ticks back inside the old extreme after the failed break, and an initial protective stop just beyond the current session extreme. Source descriptions vary or become discretionary on trailing, re-entry after a stop and holding duration. D044 therefore freezes the entry/initial-stop structure and uses a separate deterministic Guardian H24 reference exit.

## Frozen hypothesis

Across the six-market Guardian/FundedNext universe, does a source-aligned Turtle Soup failed 20-day breakout entry produce positive, broad and cost-robust executable edge when measured with the same simple H24 reference exit and source-style structural initial stop?

## Frozen universe

- BTCUSD
- ETHUSD
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Account currency: USD.
Prop-firm cost profile: FundedNext.
Tester reference model: **Model 0 / Every tick**.
Execution timeframe: M15 harness with D1 reference bars and tick-level execution.

## Frozen entry rules

All D1 references are completed **broker D1 bars**. Current-day penetration and entries use executable tester ticks.

### LONG

1. At current broker-day start, inspect the previous 20 completed D1 bars.
2. Let `prior_20d_low` be the minimum low in those 20 bars. If tied, use the most recent occurrence for age testing.
3. The most recent occurrence of `prior_20d_low` must be at least **4 completed trading sessions** before the current day (`age >= 4`). Otherwise no LONG Turtle Soup setup is eligible that day.
4. During the current broker day, executable BID must trade **strictly below** `prior_20d_low`, creating the failed-break candidate.
5. Frozen re-entry offset = **5 trade ticks** (`5 * SYMBOL_TRADE_TICK_SIZE`). No 5-vs-10 tick sweep is allowed in V0.
6. LONG trigger = `prior_20d_low + 5 ticks`.
7. After the downside penetration, executable ASK must first be observed below the trigger, then subsequently cross/print at or above the trigger. This prevents a spread-only immediate fill being mistaken for a reversal.
8. Enter virtually at that first executable ASK.
9. Initial stop is fixed immediately at **1 trade tick below the lowest executable BID observed so far during the current broker day**.

### SHORT

Exact mirror image:

1. `prior_20d_high` is the maximum high in the previous 20 completed D1 bars; ties use the most recent occurrence for age testing.
2. Its age must be `>= 4` completed trading sessions.
3. Current executable ASK must trade strictly above the prior 20-day high.
4. SHORT trigger = `prior_20d_high - 5 trade ticks`.
5. After penetration, executable BID must first be observed above the trigger, then subsequently cross/print at or below it.
6. Enter virtually at that first executable BID.
7. Initial stop is fixed at **1 trade tick above the highest executable ASK observed so far during the current broker day**.

## Same-day / overlap policy

- Entry trigger is valid only on the broker day that creates the new 20-day extreme.
- Maximum one D044 entry per broker day per symbol.
- No source re-entry after stop in V0.
- No pyramiding.
- One active D044 trade per symbol. While a prior H24 trade remains active, no new D044 entry may be opened on that symbol.
- If LONG and SHORT entry triggers become executable on the same tick before any entry is chosen, mark the broker day ambiguous and skip it rather than infer favorable ordering.

## Frozen original management for V0 scoring

The source-management layer is deliberately **not** optimized or reconstructed.

- Initial structural stop: as defined above.
- No TP.
- No BE move.
- No partial.
- No trailing.
- No indicator or regime filter.
- If the initial stop is touched first, close at the first executable BID (LONG) or ASK (SHORT), retaining gap/slippage.
- Otherwise close the full virtual position at the first executable liquidation tick at or after **entry + 24 hours** (`H24_REFERENCE`).
- Tester-end closure is allowed only as an evidence boundary condition and is reported separately.

This H24 exit is a **Guardian research reference**, not claimed to be the Street Smarts exit rule.

## Cost model

Same frozen FundedNext transport used by the current Guardian price-action harnesses:

- spread: actual executable tester BID/ASK;
- Forex: USD 5/lot/side;
- metals: 0.0016% notional/side;
- crypto: 0.04% notional/side;
- commission stress: 1.5x;
- no swap model is added for the H24 screening reference; this is a limitation to be revisited only after a positive entry result.

## Trade Path

D044 must emit native Trade Path telemetry under `research/runner/TRADE_PATH_DATASET_SPEC.md` using the frozen original initial-risk denominator:

- MFE/MAE;
- 0.5R/1R/2R/3R/5R first touches;
- MAE before milestones;
- post-1R/2R/3R min/max;
- path ambiguity flag;
- original stop/H24/test-end exit.

Trade Path is descriptive and cannot rescue a rejected D044 entry verdict.

## Stage plan

### Smoke — October 2023

Symbols: USDJPY, XAUUSD, BTCUSD.
Role: engineering only.

Required:
- compile errors = 0;
- compile warnings = 0;
- clean INIT/READY/FINAL lifecycle;
- opened = closed = CSV trade rows = path rows;
- invalid price/risk/PnL/path events = 0;
- required Trade Path fields present and parseable.

Smoke P/L must not be used for alpha selection.

### Development — 2024-01-02 through 2025-12-31

All six symbols.

Frozen gates:
- aggregate trades >= **120**;
- each symbol trades >= **10**;
- aggregate mean net R >= **+0.05R/trade**;
- aggregate PF >= **1.10**;
- positive symbols >= **4/6**;
- aggregate 2024 total > 0;
- aggregate 2025 total > 0;
- aggregate 1.5x commission-stress total > 0;
- maximum single positive-symbol contribution share <= **60%**;
- integrity events = 0.

Pass verdict: `CANDIDATE_CONFIRM`.
Failure verdict: `REJECT_V0`.

These frequency thresholds are intentionally much lower than D046's mistaken calendar-style count gate because D044 is an event setup, not a daily schedule. They are frozen before D044 outcomes are inspected.

### Confirmation — 2026-01-02 through 2026-06-30

Locked unless development passes every gate.

Frozen confirmation gates:
- aggregate trades >= **30**;
- aggregate mean net R > 0;
- aggregate PF >= **1.08**;
- positive symbols >= **3/6**;
- aggregate 1.5x commission-stress total > 0;
- integrity events = 0.

Pass verdict: `CONFIRMED`.
Failure verdict: `UNCONFIRMED`.

## Anti-overfitting / interpretation policy

- No 5/6/7/8/9/10 tick grid.
- No alternate lookback grid.
- No symbol deletion after seeing results.
- No weekday, ATR, slope, OI, RSI, EMA, regime or volatility filter in D044 V0.
- No post-hoc source-manager reconstruction to rescue V0.
- If D044 V0 rejects, saved Trade Path can generate a separately preregistered management hypothesis, but D044 remains rejected.
- If D044 development passes, confirmation is opened unchanged on 2026 H1.

## Source-reconstruction boundary

The core rules above are aligned to multiple published transcriptions of the Turtle Soup section of *Street Smarts*: new 20-period extreme, prior extreme at least four sessions old, 5–10 tick re-entry inside the old extreme, stop one tick beyond the current day's extreme, with trailing/re-entry management afterward. D044 freezes the lower source-allowed 5-tick offset before testing and explicitly labels H24 as Guardian transport. It must not be described later as an exact full-book replication.
