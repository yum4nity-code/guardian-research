# D039 — Inside-Day Breakout V0 — Preregistration

Date frozen: 2026-09-07 Europe/Paris
Status: **PREREGISTERED / NO RESULTS SEEN FOR D039**

## Scientific role

D039 is a new hypothesis generated after D038 NR7 showed a materially positive but formally rejected DEV result. D039 is **not** a rescue of D038 and may not alter D038's `REJECT_V0` verdict.

Because the choice of another contraction/expansion setup was motivated by D038's 2024-2025 evidence, D039's 2024-2025 period is development only. It is not independent confirmation even though D039 itself has not yet been executed. Only the locked 2026 H1 window may serve as prospective confirmation if every frozen DEV gate passes.

External basis:
- Toby Crabel, *Day Trading with Short Term Price Patterns and Opening Range Breakout* (1990): inside-day / narrow-range contraction and subsequent expansion framework.
- This implementation is an explicit Guardian adaptation, not a claim of exact replication of every Crabel opening-range/stretched-entry convention.

## Question

Does a strict previous-day inside-day contraction followed by the first executable break of that inside day's range produce a broad, cost-robust intraday edge across the six-market Guardian/FundedNext universe?

## Universe

- BTCUSD
- ETHUSD
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Account currency: USD.
Execution chart/timeframe: M15 tester, tick-by-tick reference model (`Model=0`).
Reference bars: broker D1.

## Frozen setup

For broker day D, define:
- `ID = D-1`
- `MOTHER = D-2`

D-1 is a **strict inside day** iff:

`High(ID) < High(MOTHER)` AND `Low(ID) > Low(MOTHER)`.

Equality at either boundary does not qualify.

Both completed D1 bars must contain finite positive prices and strictly positive ranges. Missing/unusable reference history skips the day and is counted; it does not create synthetic prices or P/L.

No NR4/NR7 condition is added. No trend or direction filter is added.

## Frozen entry

On the next broker day D:
- LONG trigger: first executable tick where ASK >= High(ID).
- SHORT trigger: first executable tick where BID <= Low(ID).
- First side touched wins.
- Entry is the actual observed ASK for long or BID for short; a gap beyond the level receives the worse observed executable price.
- If the same tick simultaneously satisfies both sides because the executable spread spans the whole inside range, skip that day as ambiguous.
- Maximum one trade per setup/day/symbol.
- No reversal and no second entry after a stop.

## Frozen initial stop and exit

Initial stop:
- LONG: Low(ID).
- SHORT: High(ID).

No TP.
No partial.
No break-even.
No trailing.
No time-of-day filter.
No RSI/EMA/ADX/ATR/news/regime filter.

Exit:
1. initial stop using executable liquidation side; otherwise
2. final executable tick before broker-day change; otherwise
3. final tester tick at test end.

No overnight carry beyond the broker day.

## Costs

Same frozen FundedNext cost model used by D038:
- Forex: USD 5/lot/side.
- Metals: 0.0016% × lot × contract size × side execution price, per side.
- Crypto: 0.04% × lot × contract size × side execution price, per side.
- Spread: native executable BID/ASK from tester ticks.
- Stress: 1.5× commission while retaining native spread.

## Native Trade Path

Every valid trade must satisfy `research/runner/TRADE_PATH_DATASET_SPEC.md` and record at minimum:
- MFE R / MAE R;
- time to MFE / MAE;
- first touch +0.5R / +1R / +2R / +3R / +5R;
- time to each milestone;
- MAE before each milestone;
- min/max R after first +1R / +2R / +3R;
- max retracement from MFE;
- path ambiguity flag/reason.

Trade Path is descriptive evidence for later Exit Lab work. It does not modify D039 V0 entry verdict.

## Engineering smoke

Period: 2023-10-02 through 2023-10-31.
Symbols: USDJPY, XAUUSD, BTCUSD.

Smoke is engineering-only and has no alpha verdict. Required:
- compile 0 errors / 0 warnings;
- `FINAL` lifecycle;
- opened = closed = CSV rows = path rows;
- zero invalid-price / invalid-risk / PnL-calc / path-calc failures;
- all required Trade Path fields present and parseable;
- no source/output provenance mismatch.

## Development — frozen before D039 execution

Period: 2024-01-02 through 2025-12-31.
Symbols: all six.

All gates must pass:
- aggregate n >= 480;
- each symbol n >= 50;
- aggregate mean net R >= +0.05;
- aggregate PF >= 1.10;
- at least 4/6 symbols have positive total net R;
- aggregate 2024 total net R > 0;
- aggregate 2025 total net R > 0;
- aggregate 1.5× commission-stress total net R > 0;
- maximum positive-symbol contribution share <= 60%;
- zero integrity events.

Any failure => `REJECT_V0` and confirmation remains unopened. No filter or threshold rescue is permitted.

## Confirmation — locked

Period: 2026-01-02 through 2026-06-30.
Symbols: all six.

This window stays unopened unless every DEV gate passes.

Frozen gates:
- aggregate n >= 120;
- aggregate mean net R > 0;
- aggregate PF >= 1.08;
- at least 3/6 symbols positive;
- aggregate 1.5× commission-stress total net R > 0;
- zero integrity events.

Fail => `UNCONFIRMED`.

## Forbidden post-hoc changes

After DEV results are seen, D039 V0 may not be rescued by:
- changing inside-day equality semantics;
- adding NR4/NR7;
- changing the reference or mother day;
- symbol deletion (including ETH);
- direction deletion;
- weekday/hour/session filters;
- RSI/EMA/ADX/ATR/volume/news/regime filters;
- stop/target/trailing/BE/partial tuning;
- changing development gates;
- opening 2026 confirmation after any DEV gate failure.

Any later hypothesis inspired by D039 must receive a new experiment ID and preregistration.
