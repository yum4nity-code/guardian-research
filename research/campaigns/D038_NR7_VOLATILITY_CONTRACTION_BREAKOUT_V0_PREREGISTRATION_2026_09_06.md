# D038 — NR7 Volatility Contraction Breakout V0 — Preregistration

Date frozen: 2026-09-06
Status: PREREGISTERED BEFORE ANY D038 RESULT INSPECTION

## Research question

Can a simple NR7 daily volatility-contraction setup followed by a next-session price breakout produce a positive, broad, cost-robust intraday edge across the six-market Guardian/FundedNext universe, while producing native Trade Path telemetry for later exit research?

## Documented basis

The setup is based on Toby Crabel's Narrow Range 7 (NR7) concept: a completed daily bar is NR7 when its high-low range is strictly smaller than the ranges of each of the previous six completed daily bars. The next session trades a breakout of the NR7 bar's high or low.

Reference descriptions consulted before freezing the experiment:

- Toby Crabel, *Day Trading with Short Term Price Patterns & Opening Range Breakout* (1990), NR7 / volatility-contraction family.
- StockCharts ChartSchool, “Narrow Range Day NR7”: NR7 is the narrowest range in seven days; upside breakout above the NR7 high and downside breakdown below the NR7 low.
- OxfordStrat, “Price Breakout with NR7 Pattern”: documents the NR7 setup and price-breakout entry, including application across a 42-futures multi-sector portfolio.

These references motivate the hypothesis only. No external backtest result is used as a Guardian acceptance criterion.

## Frozen universe

- BTCUSD
- ETHUSD
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Account currency: USD.
Prop-firm cost profile: FundedNext.
Execution model: MT5 Strategy Tester reference Model=0 / Every tick.
Tester chart period: M15; strategy decisions are tick-executed from broker D1 reference levels and do not depend on M15 OHLC ordering.

## D1 setup

For broker day D, inspect the seven completed broker D1 bars D-1 through D-7.

For each completed day i:

`range_i = High_i - Low_i`

D-1 is an NR7 setup only if:

1. all seven reference bars have finite positive prices and strictly positive ranges;
2. `range_(D-1)` is strictly smaller than each of `range_(D-2)` through `range_(D-7)`.

Ties are NOT NR7.

If any required reference bar is unavailable, invalid, non-finite or has a non-positive range, broker day D is non-tradable for D038. This is a skipped setup day, not an alpha loss and not permission to substitute another lookback.

## Frozen entry

Only the broker day immediately following a valid NR7 setup is eligible.

- Long trigger: NR7 high.
- Short trigger: NR7 low.
- Long is triggered when executable ask reaches or exceeds the NR7 high.
- Short is triggered when executable bid reaches or falls below the NR7 low.
- The first trigger reached wins.
- If both are simultaneously true on the same tick, mark the day ambiguous and do not trade.
- Fill uses the observed executable tick price: current ask for long, current bid for short. Gaps therefore receive the worse observed executable price naturally.
- Maximum one trade per broker day / NR7 setup.
- No reversal.
- If neither trigger occurs before the broker day ends, the setup expires.

No EMA, RSI, ATR, ADX, trend, weekday, time-of-day, news, regime, direction, symbol-specific or discretionary filter is allowed in V0.

## Frozen initial stop

The initial stop uses the opposite extreme of the NR7 setup bar:

- Long stop: NR7 low, evaluated on executable bid.
- Short stop: NR7 high, evaluated on executable ask.

Initial risk is frozen at entry from the actual executable entry price to that opposite NR7 extreme using `OrderCalcProfit` for one lot. The initial R denominator is never changed later.

If entry price, stop price or calculated initial risk is invalid/non-finite/non-positive, the run is an engineering/integrity failure, not a strategy rejection.

## Frozen exit

No TP, no trailing, no break-even, no partial close and no post-entry filter.

Exit is the first of:

1. initial stop; or
2. last executable tick observed before the broker day changes; or
3. final executable tick at tester termination.

The strategy does not carry positions overnight.

## Costs

Same frozen FundedNext cost model used by the common Guardian research stack:

- Forex: USD 5 per lot per side.
- Metals: 0.0016% of notional per side.
- Crypto: 0.04% of notional per side.
- Spread: executable bid/ask observed by the tester.
- Commission stress: x1.5 commission.

Primary scientific metrics use net R after baseline commission. Stress metrics use x1.5 commission.

## Native Trade Path requirement

D038 must implement `research/runner/TRADE_PATH_DATASET_SPEC.md` natively during the original tester run.

At minimum each completed trade must record, using executable liquidation-side prices and the frozen initial R denominator:

- stable trade id;
- MFE_R and MAE_R;
- MFE/MAE timestamps and time-to values;
- maximum retracement from MFE;
- reached and first-touch time for +0.5R, +1R, +2R, +3R and +5R;
- MAE observed before each reached favorable milestone;
- min/max R after first reaching +1R, +2R and +3R;
- trade duration;
- path ambiguity flag/reason.

Because D038 uses Model=0 tick execution, path ordering should normally be exact at tester-tick resolution. Any unresolved ambiguity must be flagged rather than optimistically inferred.

Trade Path data are descriptive only. They cannot alter D038 V0's frozen entry verdict. Any later stop/TP/BE/trailing/runner hypothesis becomes a separately preregistered Exit Lab experiment.

## Stage 0 — engineering smoke

Period: 2023-11-01 through 2023-11-30.
Symbols: USDJPY, XAUUSD, BTCUSD.

Smoke is engineering-only. Do not inspect profitability as an alpha decision.

Required:

- compile: 0 errors / 0 warnings;
- lifecycle clean;
- source/version identity exact;
- opened = closed = trade rows = path rows;
- invalid price/risk/PnL/path events = 0;
- deterministic STATS/TRADES output;
- native Trade Path fields present and parseable.

Any smoke engineering failure is fixed without changing frozen strategy semantics, then smoke restarts. Smoke results are not included in DEV scoring.

## Stage 1 — development

Period: 2024-01-02 through 2025-12-31.
Universe: all six symbols.

Frozen DEV gates:

- aggregate trades >= 480;
- each symbol trades >= 50;
- aggregate mean net R >= +0.05;
- aggregate Profit Factor >= 1.10;
- at least 4 of 6 symbols positive total net R;
- aggregate 2024 total net R > 0;
- aggregate 2025 total net R > 0;
- aggregate total net R under x1.5 commission stress > 0;
- no single positive symbol contributes >60% of total positive-symbol net R;
- integrity events = 0.

Any failed DEV gate => `REJECT_V0`.

No rescue tuning, symbol deletion, alternative NR lookback, alternate stop, time filter or post-hoc threshold selection is allowed after seeing DEV.

## Stage 2 — untouched confirmation

Period: 2026-01-02 through 2026-06-30.
Universe: all six symbols.
Locked until every DEV gate passes.

Frozen confirmation gates:

- aggregate trades >= 120;
- aggregate mean net R strictly > 0;
- aggregate Profit Factor >= 1.08;
- at least 3 of 6 symbols positive total net R;
- aggregate total net R under x1.5 commission stress > 0;
- integrity events = 0.

Failure => `UNCONFIRMED` with no rescue tuning.

## Scientific separation

The D038 decision pipeline is:

`entry strategy -> frozen decision score -> REJECT_V0 or CANDIDATE_CONFIRM`

The separate descriptive pipeline is:

`same validated trades -> rich score + Trade Path Dataset -> future hypothesis generation`

Trade Path findings may inspire a new Exit Lab experiment but can never retroactively convert a D038 rejection into a pass.
