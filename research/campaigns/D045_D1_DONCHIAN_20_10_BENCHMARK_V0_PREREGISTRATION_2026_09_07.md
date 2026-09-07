# D045 — D1 Donchian 20/10 Benchmark V0

Date: 2026-09-07 Europe/Paris
Status: **PREREGISTERED BEFORE D045 OUTCOME INSPECTION**
Classification: `DAILY_TREND_FOLLOWING_BENCHMARK_CFD_TRANSFER`

## Purpose
Test a deliberately slow, price-only daily trend-following benchmark on the six-market Guardian/FundedNext CFD universe. D045 is not intended to be the main challenge-finishing engine. Its role is to establish whether a classic daily Donchian/Turtle-style shape survives executable CFD spread and commission costs and can contribute an independent trend-following sleeve.

This is a **Guardian benchmark adaptation**, not a claim of exact historical Turtle System 1 replication.

## Historical rule basis
The Original Turtle Trading Rules describe System 1 as an intraday break above/below the preceding 20-day extreme, a 10-day opposite-channel exit, volatility unit `N` based on a 20-day exponential average of True Range, and a 2N protective stop. The historical System 1 also used a prior-breakout winner skip rule, pyramiding and portfolio unit limits.

Reference basis used before this preregistration:
- Curtis Faith, *Original Turtle Trading Rules* / bonus chapter reproduced in *Way of the Turtle*;
- OriginalTurtles.org 2003 rules as publicly reproduced by archival mirrors;
- independent cross-checks of the 20-day entry / 10-day exit / 2N stop structure.

D045 intentionally removes the skip rule, pyramiding and historical portfolio unit allocation so the experiment measures a simple one-position-per-symbol CFD benchmark. Those omissions are frozen **before** D045 results are opened and must not later be presented as exact Turtle replication.

## Frozen universe and execution
- Symbols: `BTCUSD`, `ETHUSD`, `EURUSD`, `GBPUSD`, `USDJPY`, `XAUUSD`.
- Account currency: USD.
- Tester chart timeframe: M15.
- Signal/reference timeframe: broker D1.
- MT5 tester model: `0` (`Every tick`).
- No orders are sent; virtual executable-side simulation only.
- One open position maximum per symbol.
- Maximum one new entry per broker day.
- No pyramiding, no partials, no TP, no BE, no discretionary filter.

## Frozen D1 reference construction
For each broker day D, use only completed D1 bars.

Entry channel:
- upper = highest high of D-1 through D-20;
- lower = lowest low of D-1 through D-20.

Exit channel:
- long exit level = lowest low of D-1 through D-10;
- short exit level = highest high of D-1 through D-10.

The current incomplete D1 bar is never included in a reference channel.

## Frozen volatility N and initial stop
`N20` is the broker D1 ATR(20) value from the previous completed D1 bar, using MT5's Wilder-style smoothed True Range implementation. This is frozen before results.

At executable entry:
- LONG initial hard stop = actual ASK entry - `2 * N20`;
- SHORT initial hard stop = actual BID entry + `2 * N20`.

The actual money loss from entry to this 2N stop for one lot, calculated through `OrderCalcProfit`, defines frozen initial `1R`. Position sizing is not part of this virtual harness; R normalization is used only to compare outcomes across markets.

## Frozen entry
While flat during broker day D:
- LONG when actual ASK first reaches/exceeds the frozen 20-day upper channel;
- SHORT when actual BID first reaches/falls below the frozen 20-day lower channel.

Actual observed ASK/BID is the fill. A gap through the breakout is therefore filled worse naturally.

If both long and short entry conditions are true on the same tick, the day is marked ambiguous and no entry is allowed that day.

No historical System-1 prior-winner skip rule is used in D045 V0.

## Frozen exit
While long, exit the full virtual position at the first actual BID tick satisfying either:
- BID <= frozen 2N hard stop; or
- BID <= current broker day's frozen 10-day low exit channel.

While short, exit at the first actual ASK tick satisfying either:
- ASK >= frozen 2N hard stop; or
- ASK >= current broker day's frozen 10-day high exit channel.

If stop and Donchian exit are both crossed on the same observed tick, the actual executable price is identical for PnL; record deterministic reason `STOP_AND_DONCHIAN` and do not synthesize an earlier fill.

Positions may cross broker days and weekends. There is no EOD flattening. At tester end, any open position closes at the final executable liquidation tick and is labeled `TEST_END`.

## Costs
Use the existing frozen Guardian/FundedNext executable-cost model:
- spread: naturally embedded by ASK entry / BID long liquidation and BID entry / ASK short liquidation;
- Forex: USD 5 per lot per side;
- metals: 0.0016% notional per side;
- crypto: 0.04% notional per side;
- commission stress: 1.5x explicit commission.

Historical swap is **not** reconstructed by this virtual runner. All D045 V0 formal results are therefore explicitly **net ex-swap**. A positive D045 result cannot authorize production until a separate, preregistered FundedNext swap/weekend stress is passed. This limitation is material because D045 can hold positions for multiple days.

## Native Trade Path
Every trade must emit the canonical native Trade Path dataset already used by D038-D040:
- executable-side MFE/MAE and times;
- time to MFE/MAE;
- max retracement from MFE;
- first touch + time-to + MAE-before for +0.5R/+1R/+2R/+3R/+5R;
- post-first-1R/2R/3R min/max;
- ambiguity fields.

Trade Path analytics remain descriptive only and cannot rescue the frozen parent verdict.

## Engineering smoke
Window: `2023-08-01` through `2023-10-31`.
Symbols: `USDJPY`, `XAUUSD`, `BTCUSD`.

Smoke is engineering-only. No profitability or alpha conclusion may be drawn from it.

PASS only if:
- compile errors = 0, warnings = 0;
- deterministic STATS/TRADES files exist;
- lifecycle closes cleanly;
- opened = closed = CSV trade rows = native path rows;
- invalid price/risk/PnL/path events = 0;
- required Trade Path fields are present and parseable.

## Frozen development stage
Window: `2024-01-02` through `2025-12-31`.
All six symbols.

D045 V0 advances only if **all** are true:
1. aggregate trades >= 120;
2. every symbol >= 10 trades;
3. aggregate mean net ex-swap R >= +0.10R/trade;
4. aggregate PF >= 1.20;
5. at least 4/6 symbols have positive total net R;
6. aggregate 2024 net R > 0;
7. aggregate 2025 net R > 0;
8. aggregate result remains positive at 1.5x commission;
9. no positive symbol contributes >60% of pooled positive net R;
10. integrity events = 0.

Any failure => `REJECT_V0`. No post-hoc rescue, no threshold tuning on DEV.

## Frozen confirmation stage
Locked unless DEV passes.

Window: `2026-01-02` through `2026-06-30`.
All six symbols.

Confirmation requires **all**:
1. aggregate trades >= 36;
2. aggregate mean net ex-swap R > 0;
3. aggregate PF >= 1.10;
4. at least 3/6 symbols positive;
5. aggregate result remains positive at 1.5x commission;
6. integrity events = 0.

Failure => `UNCONFIRMED`.

Even `CONFIRMED` means only **confirmed net-ex-swap benchmark edge on this CFD feed**. It still requires explicit FundedNext swap/weekend stress and portfolio overlap/risk analysis before Guardian integration.

## Scientific boundaries
- Do not add the historical previous-winner skip rule after seeing D045 V0 outcomes.
- Do not add pyramiding after seeing D045 V0 outcomes.
- Do not change 20/10, 2N, N20, direction, symbol set, dates or cost model after DEV is opened.
- Do not use native Trade Path to relabel a failed parent experiment.
- D045 is an independent daily trend benchmark relative to the intraday contraction family, but it is not expected to provide high challenge cadence by itself.
