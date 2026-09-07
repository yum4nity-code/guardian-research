# D053 — FundedNext US Index ORB30 Entry-Alpha Benchmark V0 — Preregistration

Date: 2026-09-07 Europe/Paris
Status: **PREREGISTERED BEFORE ANY D053 MT5 OUTCOME**
Classification: ENTRY_ALPHA / INTRADAY OPENING-RANGE BREAKOUT

## Purpose

Test one simple, mechanical Opening Range Breakout benchmark on four US equity-index CFDs under the FundedNext execution environment.

This is deliberately an **entry-alpha** experiment. It does not test a grid of ORB widths, take-profits, breakeven rules, trailing stops, volume filters, trend filters, weekdays, volatility regimes or symbol subsets.

The strong management-as-alpha claim was tested separately in D052 and failed. D053 therefore returns to the question: **does a simple session-open price structure itself contain robust directional information?**

## Research basis and replication boundary

Opening Range Breakout is a documented intraday breakout family. Published research includes:
- Holmberg, Lönnbark & Lundström (2013), *Assessing the profitability of intraday opening range breakout strategies*, Finance Research Letters 10(1), 27–33, DOI 10.1016/j.frl.2012.09.001.
- Tsai et al. (2019), *Assessing the Profitability of Timely Opening Range Breakout on Index Futures Markets*, IEEE Access 7, 32061–32071, DOI 10.1109/ACCESS.2019.2899177.
- The family is historically associated with Toby Crabel's 1990 opening-range work.

D053 is **not claimed as an exact replication** of Crabel, Holmberg et al., or Tsai et al. It is a Guardian/FundedNext benchmark with rules frozen below before outcome inspection.

FundedNext currently lists SPX500, NDX100, US30 and US2000 as tradable index CFDs. FundedNext also states that server time is GMT+3 during daylight-saving periods and GMT+2 otherwise. D053 intentionally uses a **fixed FundedNext server-time anchor**, not an inferred exchange timestamp.

Operational source references:
- https://help.fundednext.com/en/articles/8224087-fundednext-tradable-assets-what-can-i-trade-on-fundednext-cfd-accounts
- https://help.fundednext.com/en/articles/8019672-what-is-fundednext-s-server-time
- https://help.fundednext.com/en/articles/9857265-trading-session-time

## Frozen universe

Exactly:
- SPX500
- NDX100
- US30
- US2000

No symbol may be dropped, added, or promoted after seeing D053 development outcomes.

## Frozen tester model

- MT5 timeframe: M15
- Strategy Tester model: **0 / Every tick**
- Account currency: USD
- Sequential local MT5 only
- No real orders; the EA is a virtual research harness
- Executable ASK/BID ticks drive range construction, entry, stop and liquidation

## Frozen broker-time opening range

For each FundedNext server date:

1. Opening range collection begins at **16:30:00 server time**.
2. Opening range collection ends immediately before **17:00:00 server time**.
3. `OR_ASK_HIGH` = highest executable ASK observed during 16:30:00–16:59:59.
4. `OR_BID_LOW` = lowest executable BID observed during 16:30:00–16:59:59.
5. The day is unusable if the range contains no executable ticks, prices are invalid, or `OR_ASK_HIGH <= OR_BID_LOW`.
6. This 16:30 server-time anchor is the actual tested rule. It is chosen as an operational proxy for the US cash-open region under FundedNext's seasonal GMT+2/GMT+3 server clock. DST transition mismatch days, if any, are retained; they are not corrected after results.

No pre-open data, D1 trend, overnight gap, volume, ATR, RSI, moving average or volatility filter participates in the entry.

## Frozen entry

From **17:00:00 server time** until immediately before **22:45:00 server time**:

- `trade_tick` = `SYMBOL_TRADE_TICK_SIZE`; if unavailable/nonpositive the run is invalid.
- LONG trigger = executable ASK >= `OR_ASK_HIGH + 1 trade_tick`.
- SHORT trigger = executable BID <= `OR_BID_LOW - 1 trade_tick`.
- First trigger wins.
- LONG enters at the observed ASK.
- SHORT enters at the observed BID.
- If both triggers are simultaneously true on the same tick, the day is marked ambiguous and skipped.
- Maximum one trade per symbol/server-day.
- No reversal and no re-entry.

## Frozen initial risk and exit

Initial stop:
- LONG: `OR_BID_LOW`
- SHORT: `OR_ASK_HIGH`

`1R` is the executable 1-lot money loss from entry to that frozen initial stop, calculated with `OrderCalcProfit`.

Management:
- no take-profit;
- no breakeven move;
- no trailing;
- no partial;
- no time-varying stop.

Exit:
1. structural stop on the first executable crossing, or
2. first executable liquidation tick at/after **22:45:00 server time**, or
3. tester-end fallback only for engineering closure.

A broker-day change with an unresolved open trade before the fixed liquidation is an engineering invalidity, not a strategy loss.

## Cost model

Primary result already embeds the tester's executable bid/ask spread:
- LONG enters ASK and exits BID;
- SHORT enters BID and exits ASK.

No additional explicit index commission is added in V0, preserving the index treatment already used in Guardian's FundedNext market-transport work.

Spread stress:
- record entry and exit executable spreads;
- estimate the observed round-trip spread penalty relative to mid as 0.5 × (entry spread + exit spread);
- `1.5x spread stress` subtracts an **additional 0.5× observed spread penalty**, i.e. extra adverse price distance = 0.25 × (entry spread + exit spread), translated to 1-lot USD and R.
- This stress rule is frozen before D053 outcomes.

Swap is excluded because all valid trades liquidate intraday.

## Native path telemetry

For each trade export, on executable liquidation prices:
- MFE in initial R;
- MAE in initial R;
- time to MFE;
- time to MAE;
- maximum retracement from MFE.

This telemetry is descriptive only during D053. It may support a separately preregistered management study later, but cannot alter the D053 verdict.

## Engineering smoke

Window:
`2023-10-02` through `2023-10-31`

Symbols:
- SPX500
- NDX100
- US2000

Smoke is engineering-only. Profitability must not be interpreted.

Smoke passes only if:
- source compiles 0 errors / 0 warnings;
- each symbol produces at least one usable opening range;
- at least one trade closes across the smoke batch;
- opened == closed == CSV rows for every symbol;
- no invalid price/risk/PnL/path event;
- no day-change unresolved trade;
- fixed output identity and source SHA match.

Only a clean smoke unlocks DEV.

## Frozen development

Window:
`2024-01-02` through `2025-12-31`

Symbols:
all four frozen markets.

All gates are required:

1. aggregate trades >= **1000**;
2. each symbol trades >= **200**;
3. aggregate mean net R >= **+0.050R/trade**;
4. aggregate PF >= **1.10**;
5. aggregate total net R > 0;
6. 1.5x spread-stress total net R > 0;
7. at least **3/4 symbols** have positive total net R;
8. aggregate 2024 total net R > 0;
9. aggregate 2025 total net R > 0;
10. month-block bootstrap 95% lower bound of aggregate mean net R > 0;
11. maximum positive-symbol contribution share <= **0.55**;
12. integrity events = 0.

Side attribution (LONG/SHORT) is reported but is **not** a gate. If only one direction carries the edge, D053 still retains its frozen bidirectional verdict; any later one-direction hypothesis must be a new preregistration and may not rewrite D053.

If any gate fails:
`D053_REJECT_V0`
and no confirmation is opened.

If every gate passes:
`D053_DEV_PASS_HOLDOUT_LOCKED`
and exactly the unchanged D053 rule becomes eligible for a separate confirmation command.

No DEV threshold may be waived or rounded.

## Locked confirmation holdout

The confirmation reserve is:
`2026-07-01` through `2026-08-31`

Why this period:
- prior Guardian experiments have already exposed 2026-H1 index outcomes;
- Guardian policy treats once-seen data as no longer untouched;
- Jul-Aug 2026 remains reserved for D053 and must not be opened by the DEV command.

Frozen confirmation gates:
1. aggregate n >= **100**;
2. each symbol n >= **20**;
3. aggregate mean net R > 0;
4. PF >= **1.05**;
5. total net R > 0;
6. 1.5x spread-stress total net R > 0;
7. at least **3/4 symbols** positive;
8. day-block bootstrap 95% lower bound of mean net R > 0;
9. integrity events = 0.

Failure: `D053_UNCONFIRMED_CLOSE`.
Pass: `D053_CONFIRMED_ENTRY_ALPHA`, still subject to portfolio/risk/production review.

## Anti-overfitting / decision policy

Forbidden after DEV is opened:
- changing the 30-minute range;
- changing 16:30/17:00/22:45 times;
- changing the one-tick breakout buffer;
- changing the opposite-range stop;
- adding filters;
- dropping a losing symbol;
- selecting only LONG or only SHORT;
- changing gates;
- promoting a near-pass;
- inspecting Jul-Aug 2026 unless every DEV gate passes.

A result is a strategy rejection only when engineering integrity is valid. Missing data, missing symbol, compile error, corrupt CSV or lifecycle error is `ENGINEERING_INCOMPLETE`, not `REJECT_V0`.

## Production boundary

Even a confirmed D053 does not authorize Guardian Core integration. Production promotion requires:
- exact current FundedNext rule/cost review;
- portfolio overlap and risk-budget analysis;
- Guardian v12.01 non-regression;
- live-forward execution sanity;
- explicit production review.
