# D026 V0 — first run + implementation conformance finding

Date: 2026-09-04
Status: FIRST DATA RECEIVED / DATA INTEGRITY GOOD / STRATEGY VERDICT WITHHELD / V0 1.00 IMPLEMENTATION NON-CONFORMANT TO PRE-RESULT RULE LOCK

## 1. User-supplied first-run files

Received cumulative files:
- `d026_per_virtual_v0_events.csv`
- `d026_per_virtual_v0_trades.csv`
- `d026_per_virtual_v0_outcomes.csv`

Unexpectedly useful extra coverage: the user ran five 2024-2025 sessions, not only BTC/ETH.

Sessions / virtual signals:
- BTCUSD: 560 = 283 in 2024 + 277 in 2025
- ETHUSD: 618 = 332 + 286
- DOGUSD: 525 = 269 + 256
- LNKUSD: 562 = 264 + 298
- XAUUSD: 649 = 357 + 292

Total virtual signals: 2,914.

Event rows: 66,241.
Outcome rows: 14,555.

No `VALID_SIGNAL_REJECTED_BAD_RISK` and no `VALID_SIGNAL_REJECTED_NO_SLOT` transition occurred. The count of `VALID_SIGNAL_ACCEPTANCE + VALID_SIGNAL_RETEST` equals the trade count for every symbol.

Every trade has at least one outcome row. 48h completion is nearly complete; only a few end-of-test events lack the final 48h snapshot (BTC 1, DOG 4, ETH 1, LNK 3, XAU 1), consistent with the 2025-12-31 test boundary.

## 2. Predeclared analyzer output — DESCRIPTIVE ONLY UNTIL CONFORMANCE FIX

The precommitted analyzer `research/analysis/analyze_d026_per_v0.py` was applied conceptually as declared: fixed +1R/+2R/+3R first-touch EV, same-M1 ambiguity excluded, no threshold optimization.

Overall pre-cost EV from the received V0 1.00 population:

| Symbol | Signals | EV +1R | EV +2R | EV +3R | 40%@1R + BE ->2R | 40%@1R + BE ->3R |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSD | 560 | +0.011R | -0.117R | -0.176R | -0.050R | -0.098R |
| ETHUSD | 618 | -0.009R | -0.058R | -0.138R | +0.008R | -0.034R |
| DOGUSD | 525 | -0.004R | +0.077R | -0.040R | +0.023R | -0.041R |
| LNKUSD | 562 | -0.037R | -0.042R | -0.048R | -0.012R | -0.024R |
| XAUUSD | 649 | -0.007R | -0.009R | -0.101R | -0.041R | -0.109R |

If the implementation had conformed perfectly, these broad figures would already be poor for BTC/ETH and would not meet the required large-edge standard.

Predeclared year/side/path splits show mostly non-replicating regime effects. Examples:
- BTC SHORT +2R: 2024 about -0.161R vs 2025 about +0.160R.
- DOG LONG +2R: 2024 about +0.311R vs 2025 about +0.024R.
- XAU LONG +2R: 2024 about +0.369R vs 2025 about -0.348R.
- ETH RETEST flips from positive in 2024 to negative in 2025.

One descriptive branch is less inconsistent: LNK SHORT +3R is about +0.115R in 2024 and +0.200R in 2025, pooled about +0.164R. It is NOT promotable because the implementation defect below contaminates the population and because it was discovered only after seeing the first sample.

## 3. Critical static re-audit after first data — implementation does not exactly match the frozen lock

The frozen rules were created before any D026 result and remain unchanged:
`research/campaigns/D026_PRICE_EXHAUSTION_RECLAIM_V0_RULES_LOCK_2026_09_04.md`.

Re-reading the source against that lock exposed two implementation errors in `D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5`.

### A. State deadlines are off by one bar

The code increments `bars_in_state`, evaluates the transition, and only afterwards checks `> N`.

Consequence:
- displacement is allowed on a THIRD M15 bar after the sweep, although the lock allows only the next 2;
- exhaustion is allowed on a FOURTH bar after displacement, although the lock allows only the next 3;
- reclaim is allowed on a FIFTH bar after exhaustion, although the lock allows only the next 4;
- validation is allowed on a FIFTH bar after reclaim, although the lock allows only the next 4.

This is an implementation bug, not a strategy result and not a reason to edit the frozen thresholds.

### B. RETEST proximity is one-sided instead of a true +/-0.15 ATR band

Frozen rule: the relevant retest extreme must be within `0.15 x H1 ATR` around the swept level while closing on the reclaimed side.

V0 1.00 code used:
- LONG: `bar.low <= level + 0.15 ATR`
- SHORT: `bar.high >= level - 0.15 ATR`

Those tests also accept arbitrarily deep excursions beyond the level. They are too permissive relative to the locked wording.

Correct implementation is:
- LONG: `abs(bar.low - level) <= 0.15 ATR` and close > level;
- SHORT: `abs(bar.high - level) <= 0.15 ATR` and close < level.

## 4. Scientific consequence

The first V0 1.00 data are useful as a smoke/instrumentation test, but **must not be used for a final D026 strategy verdict**.

The rules lock is not changed. The implementation is corrected to the already-existing lock.

Do NOT retune displacement, exhaustion, ATR, level, side or path thresholds based on these results.

## 5. Conformance fix

New implementation-only wrapper:
- `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_01_CONFORMANCEFIX.mq5`
- creation commit: `d0c15e2f901a73f51d09cd08394b3371e625b5c8`

It includes V0 1.00 and replaces only:
- exact state-window enforcement;
- RETEST-band conformance;
- the timer path needed to call the corrected state machine.

No frozen threshold is changed.

## 6. Next test — narrow only

Do NOT rerun all five markets yet.

First corrected validation needs only:
1. BTCUSD, M1, 2024-01-01 -> 2025-12-31, Every tick, inputs `48 / 1 / true`.
2. ETHUSD, identical settings.

The corrected wrapper currently writes through the same D026 CSV logger as V0 1.00. That is acceptable because each run has a unique `session_id`; downstream analysis must isolate the new sessions rather than mixing them with the five first-run sessions.

After corrected BTC+ETH, decide whether D026 V0 deserves any further market validation. If BTC/ETH remain broadly flat/negative, reject V0 rather than tuning it.