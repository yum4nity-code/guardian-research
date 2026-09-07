# D052 — Management-as-Alpha Paired Null-Entry Lab V0 — preregistration

Date frozen: 2026-09-07 Europe/Paris
Status: **PREREGISTERED BEFORE ANY D052 OUTCOME INSPECTION**

## Scientific question

Can a plausible, fully mechanical trade-management rule create robust positive expectancy from an entry process that contains deliberately no directional signal?

This experiment directly tests the strong belief that “good management can save almost any signal.” It is not an optimization of any prior Guardian strategy and cannot rewrite D038–D051 verdicts.

## Null-entry construction

The entry process is deliberately direction-neutral.

For each eligible broker day and symbol:

1. Compute a deterministic scheduled minute from only `symbol + broker-day key`. No price, indicator, return, range, trend, volatility direction, news, weekday-selection or future data enters the scheduling hash.
2. The scheduled minute lies in broker time between **10:00 and 13:59** inclusive.
3. At the first executable tick at or after that minute, but no later than 15:00 broker time, create **two independent virtual trades simultaneously**:
   - one LONG entered at executable ASK;
   - one SHORT entered at executable BID.
4. There is at most one paired event per broker day per symbol.
5. If the scheduled event cannot be formed cleanly, the day is skipped; it is never shifted using price information.

Because both directions are entered at the same event, a directional drift or accidental directional signal cannot by itself make both sleeves profitable. Any claimed management-alpha candidate must pass separate LONG and SHORT expectancy gates.

## Risk unit

`1R` is a volatility scale, not an entry signal.

- Use ATR(14) calculated from the **14 prior completed D1 bars**, with the preceding completed close required for true-range calculation.
- No current-day or future bar information enters ATR.
- For each side, `risk_money_1lot_usd` is the absolute MT5 `OrderCalcProfit` loss for a 1-lot move of exactly 1 ATR against the entry.
- Management milestones/stops are evaluated in gross executable-side R relative to that fixed initial risk unit.

If the reference data or risk calculation is unusable, the event is skipped or the run is engineering-invalid according to the frozen integrity rules; no fallback parameter is fitted from outcomes.

## Frozen market universe

Twelve liquid FundedNext markets with already-proven local data/engineering coverage:

### Forex
- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- USDCHF

### Equity indices
- SPX500
- NDX100
- GER30
- US30

### Metals
- XAUUSD
- XAGUSD

XPTUSD is excluded **before D052 testing** because D049 repeatedly demonstrated a D1-reference engineering defect on that symbol. Crypto is excluded from V0 to avoid mixing 24/7 session structure and materially different commission mechanics into the first null-management test.

No symbol may be added, removed or substituted after D052 outcomes are inspected.

## Frozen management family

All rules operate on the exact same paired entries. Thresholds are evaluated from executable BID for long liquidation and executable ASK for short liquidation. All active-management candidates have a hard initial `-1R` stop unless explicitly stated otherwise.

### Reference — not eligible for selection

`REF_EOD_NO_STOP`
- no stop;
- no TP, BE, partial or trailing;
- exit at the last executable tick before broker-day change, or TEST_END.

This is the simple “no active management” paired-null reference.

### Candidate set — fixed before testing

1. `SL1_EOD`
   - stop at -1R;
   - otherwise EOD.

2. `SL1_TP1`
   - stop -1R;
   - full exit at +1R.

3. `SL1_TP2`
   - stop -1R;
   - full exit at +2R.

4. `SL1_TP3`
   - stop -1R;
   - full exit at +3R.

5. `SL1_BE_AFTER_1R_EOD`
   - initial stop -1R;
   - after first +1R touch, floor moves to 0R;
   - otherwise EOD.

6. `SL1_BE_AFTER_2R_EOD`
   - initial stop -1R;
   - after first +2R touch, floor moves to 0R;
   - otherwise EOD.

7. `SL1_P50_AT_1R_BE_REST`
   - initial stop -1R;
   - at first +1R touch, close 50% at the executable trigger tick;
   - remaining 50% floor moves to 0R;
   - remainder exits at floor or EOD.

8. `SL1_P40_AT_2_5R_BE_REST`
   - initial stop -1R;
   - at first +2.5R touch, close 40% at the executable trigger tick;
   - remaining 60% floor moves to 0R;
   - remainder exits at floor or EOD.

9. `SL1_TRAIL1_AFTER_1R`
   - initial stop -1R;
   - after first +1R touch, trailing floor = MFE - 1R;
   - floor can only tighten;
   - exit at floor or EOD.

10. `SL1_TRAIL1_5_AFTER_2R`
    - initial stop -1R;
    - after first +2R touch, trailing floor = MFE - 1.5R;
    - floor can only tighten;
    - exit at floor or EOD.

11. `SL1_P50_AT_1R_TRAIL1_REST`
    - initial stop -1R;
    - at first +1R touch, close 50%;
    - remaining 50% uses trailing floor = MFE - 1R;
    - floor can only tighten;
    - exit at floor or EOD.

No management threshold, fraction, trail distance, risk unit, entry schedule or symbol may be changed after outcome inspection in V0.

## Same-tick / executable convention

- LONG entry: ASK; LONG liquidation: BID.
- SHORT entry: BID; SHORT liquidation: ASK.
- Stop/TP/BE/trail triggers are detected on the current executable liquidation tick.
- Exit price is that observed executable liquidation price, not an idealized threshold price.
- When a partial threshold is first crossed, the partial is closed at that executable tick.
- MFE/MAE and trailing state are updated deterministically from the same executable-side tick stream.
- No synthetic intra-tick ordering is invented.

## Frozen cost model

Executable tester spread is inherently present through bid/ask.

Explicit commission, parent-comparable Guardian convention:
- Forex: **USD 5 per lot per side** = USD 10 round trip for 1 lot.
- Equity indices: **zero explicit commission**, executable spread retained.
- Metals: **0.0016% of notional per side**.
- Stress: **1.5x explicit commission**.

All entries and exits are same broker day by construction except TEST_END edge cases, so swap is excluded from V0 and should be immaterial to ordinary rows.

## Tester model

- FundedNext local MT5 terminal.
- Model=0 / Every Tick.
- M15 tester chart; D1 completed bars only for ATR reference.
- sequential execution only.
- USD account.
- no orders are sent; all legs are virtual simulations on executable ticks.

## Engineering smoke

Window: **2023-10-02 through 2023-10-31**.

Representative symbols:
- EURUSD
- SPX500
- XAUUSD

Engineering only. No alpha/profitability interpretation.

Smoke requires:
- compile pass with exact frozen source identity;
- lifecycle closes every virtual leg;
- all 12 management labels (reference + 11 candidates) present for both LONG and SHORT on every emitted paired event;
- no invalid price/risk/PnL/commission values;
- no duplicate event-side-management rows;
- nonzero paired events on every smoke symbol.

Only if smoke passes may the unchanged source enter development.

## Development window

**2024-01-02 through 2025-12-31**, all 12 frozen symbols.

This is management-family discovery/selection, not confirmation.

Expected scale is thousands of paired null legs, making this a high-power null test rather than a small-sample strategy screen.

## Candidate development metrics

Each candidate is evaluated against the exact same underlying entry-side events and against `REF_EOD_NO_STOP`.

For each candidate report at minimum:
- total eligible legs;
- mean/median net R;
- PF;
- total net R;
- 1.5x commission-stress total;
- LONG mean net R;
- SHORT mean net R;
- per-symbol n and total net R;
- number of positive symbols;
- 2024 and 2025 totals;
- paired candidate-minus-reference mean and total delta;
- maximum positive-symbol contribution share;
- deterministic month-block bootstrap 95% CI for absolute mean net R;
- deterministic month-block bootstrap 95% CI for paired mean delta vs reference;
- integrity events.

## Frozen development gates

A candidate is eligible for confirmation only if **every** gate passes:

1. aggregate n >= **8,000** legs;
2. each symbol n >= **600** legs;
3. aggregate mean net R > **0**;
4. PF >= **1.05**;
5. total net R > **0**;
6. 1.5x commission-stress total > **0**;
7. LONG mean net R > **0**;
8. SHORT mean net R > **0**;
9. at least **9/12** symbols positive;
10. 2024 total net R > **0**;
11. 2025 total net R > **0**;
12. paired mean candidate-minus-reference delta > **0**;
13. month-block bootstrap 95% lower bound of candidate absolute mean net R > **0**;
14. month-block bootstrap 95% lower bound of paired mean delta > **0**;
15. max positive-symbol contribution share <= **0.25**;
16. integrity events = **0**.

These intentionally demanding gates match the strength of the claim being tested. “Less negative than reference” is not enough. The management must create positive absolute expectancy after costs, on both directions, broadly across markets and years.

## Frozen selection rule

If zero candidates pass every development gate:

`D052_NO_MANAGEMENT_ALPHA_IN_FROZEN_FAMILY`

and the holdout remains unopened. No “best loser” may be promoted.

If one or more candidates pass every gate, select exactly one by this lexicographic rule:

1. highest `min(bootstrap_lower_absolute_mean, bootstrap_lower_paired_delta)`;
2. highest PF;
3. highest aggregate mean net R;
4. lowest max positive-symbol contribution share;
5. management name ascending as deterministic final tie-break.

Only that one selected candidate may proceed to holdout.

## Untouched confirmation holdout

Frozen now, before D052 development outcomes:

**2026-07-01 through 2026-08-31**, same 12 symbols.

This window was not opened for D051 because D051 failed H1 and its reserved Jul-Aug holdout stayed locked. D052 uses it only as a new, separately preregistered null-management holdout if a D052 candidate first passes every development gate.

The holdout implementation must expose only:
- `REF_EOD_NO_STOP`;
- the single mechanically selected candidate.

It must not generate holdout outcomes for the losing candidates.

Frozen holdout gates — all required:
1. aggregate n >= **800** legs;
2. each symbol n >= **60** legs;
3. aggregate mean net R > 0;
4. PF >= **1.05**;
5. total net R > 0;
6. 1.5x commission-stress total > 0;
7. LONG mean net R > 0;
8. SHORT mean net R > 0;
9. at least 9/12 symbols positive;
10. paired mean delta vs reference > 0;
11. deterministic broker-day block-bootstrap 95% lower bound of absolute mean net R > 0;
12. deterministic broker-day block-bootstrap 95% lower bound of paired delta > 0;
13. max positive-symbol contribution share <= 0.30;
14. integrity events = 0.

Pass => `D052_MANAGEMENT_ALPHA_CONFIRMED_IN_TESTED_NULL_FRAMEWORK`.

Fail => `D052_MANAGEMENT_ALPHA_UNCONFIRMED_CLOSE`.

No retuning or second-candidate holdout is permitted after the holdout is opened.

## Interpretation boundary

A D052 pass would **not** prove that management can save literally every possible signal. It would show something important but narrower: a frozen mechanical management rule can create robust positive expectancy from this deliberately direction-neutral paired-entry process across a broad liquid market set. In that case management is functioning as an alpha-bearing strategy component and must be researched as such.

A D052 failure would **not** prove that no management rule can ever create alpha. It would materially falsify the strong universal-rescue belief for this broad, preregistered family of common stop/TP/BE/partial/trailing rules.

Either result is useful.

## Prior evidence boundary

- D041 already showed one sophisticated management candidate materially degraded an already-confirmed entry edge.
- Management Benchmark V1/V2 found no universal cross-family management promotion.
- Those results motivated this null test but do not enter D052 scoring.
- D052 does not use D051’s seen 2026-H1 results and does not attempt to rescue NR7.
