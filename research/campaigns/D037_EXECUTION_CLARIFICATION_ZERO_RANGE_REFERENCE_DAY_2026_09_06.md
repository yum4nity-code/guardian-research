# D037 — Execution clarification: zero-range previous D1 bar

Date: 2026-09-06
Status: ENGINEERING CLARIFICATION AFTER INVALID HARNESS RUN, BEFORE XAUUSD ALPHA OBSERVATION

## Trigger

The first six-symbol DEV batch stopped on XAUUSD at `2024-01-02 01:15` with `FINAL_INVALID_PRICE | invalid broker-day setup price/range`.

The immutable diagnostic showed:
- symbol: XAUUSD
- bars_seen: 0
- bars_in_stage: 0
- trades_opened: 0
- trades_closed: 0
- CSV trade rows: 0
- invalid_price: 1

Therefore no XAUUSD DEV trade result or alpha information had been observed when this clarification was written.

## Clarification

The D037 strategy requires a strictly positive previous-day range to define both breakout thresholds and the initial stop distance.

If the immediately preceding completed broker D1 bar has finite, strictly positive prices but `High(D-1) == Low(D-1)`, then `prev_range == 0` and no valid D037 setup exists for the current broker day. That current day is therefore **non-tradable** and must be skipped.

This condition is not an `invalid_price` event because the market prices themselves are valid. It is a missing volatility reference for this strategy.

The harness must:
- count the day in a dedicated `no_reference_range_days` counter;
- emit a `SKIP_NO_REFERENCE_RANGE` journal line;
- open no trade on that broker day;
- continue to the next broker day;
- apply this rule identically to all six frozen symbols.

The harness must still end `FINAL_INVALID_PRICE` for any of the following:
- non-finite D1 price;
- D1 price <= 0;
- previous high < previous low;
- invalid or non-finite derived trigger;
- unresolved current/previous D1 bar;
- any invalid M15 OHLC or executable price.

For auditability, v1.02 also logs the exact current/previous D1 timestamps and OHLC values when a broker-day setup remains invalid.

## Scientific scope

This clarification does not change:
- the six-symbol universe;
- DEV or confirmation dates;
- the 0.50 previous-range breakout multiplier;
- entry-side execution rules;
- stop distance;
- ambiguity handling;
- one-trade-per-day rule;
- EOD exit;
- commission/spread model;
- any DEV or confirmation gate.

It is not a parameter rescue, symbol-specific exception, or post-result filter. It only distinguishes a valid-price day with no positive volatility reference from a genuine price-integrity failure.

The previous v1.01 XAUUSD run remains preserved as invalid engineering evidence and must not be scored.
