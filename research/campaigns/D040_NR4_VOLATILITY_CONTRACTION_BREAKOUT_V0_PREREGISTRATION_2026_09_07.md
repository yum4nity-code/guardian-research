# D040 — NR4 Volatility Contraction Breakout V0 — Preregistration

Date frozen: 2026-09-07 Europe/Paris
Status: **PREREGISTERED / NO D040 RESULTS SEEN**

## Scientific role

D040 is a new contraction-family hypothesis generated after D038 NR7 and D039 Inside-Day both produced attractive 2024-2025 development metrics but were formally rejected only because their frozen aggregate trade-count gates were missed.

D040 is **not** a rescue, continuation, or relabeling of either rejected V0. Their verdicts remain unchanged. The explicit question here is whether the less restrictive, separately documented NR4 contraction occurs often enough to satisfy the predeclared frequency requirement while retaining broad, cost-robust edge.

External basis:
- Toby Crabel's NR4 work defines a narrow-range-four day as a day whose range is narrower than each of the prior three daily ranges.
- Crabel's original work paired NR4 with an opening-range breakout on the following day.
- D040 is an explicit Guardian adaptation: after an NR4 day it trades the first executable break of the NR4 day's own high/low, preserving the same transport used in D038/D039. It is not claimed to be an exact replication of Crabel's ORB entry convention.

## Question

Does a strict previous-day NR4 contraction followed by the next broker day's first executable break of that NR4 day's range produce a sufficiently frequent, broad, positive and cost-robust intraday edge across the six-market Guardian/FundedNext universe?

## Universe

- BTCUSD
- ETHUSD
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Account currency: USD.
Execution chart/timeframe: M15 tester with tick-by-tick reference model (`Model=0`).
Reference bars: completed broker D1 bars.

## Frozen NR4 setup

For broker day D inspect completed bars D-1, D-2, D-3 and D-4.

Let `range(i) = High(i) - Low(i)`.

D-1 is a **strict NR4** iff:

`range(D-1) < range(D-2)` AND
`range(D-1) < range(D-3)` AND
`range(D-1) < range(D-4)`.

All four bars must contain finite positive prices and strictly positive ranges.

Ties do **not** qualify. No inside-day condition is added.

Missing/unusable reference history skips the broker day and is counted; it never creates synthetic prices or P/L.

## Frozen entry

On the immediate next broker day D:
- LONG trigger: first executable tick where ASK >= High(D-1 NR4).
- SHORT trigger: first executable tick where BID <= Low(D-1 NR4).
- First side touched wins.
- LONG fills at the observed ASK; SHORT fills at the observed BID. Gaps receive the worse observed executable price naturally.
- If one tick simultaneously satisfies both trigger sides because the executable spread spans the entire NR4 range, the setup is marked ambiguous and no trade is opened.
- Maximum one trade per setup/day/symbol.
- No reversal and no second entry after a stop.

## Frozen initial stop and exit

Initial stop:
- LONG: NR4 low.
- SHORT: NR4 high.

No TP.
No partial.
No break-even.
No trailing.
No time-of-day filter.
No RSI/EMA/ADX/ATR/volume/news/regime/direction/symbol filter.

Exit order:
1. initial stop using executable liquidation side; otherwise
2. final executable tick before broker-day change; otherwise
3. final tester tick at test end.

No overnight carry beyond the broker day.

## Costs

Same frozen FundedNext model as D038/D039:
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

Trade Path is descriptive evidence for later Exit Lab/attribution work. It does not alter the D040 V0 entry verdict.

## Engineering smoke

Period: 2023-10-02 through 2023-10-31.
Symbols: USDJPY, XAUUSD, BTCUSD.

Smoke is engineering-only; no alpha verdict or strategy selection is permitted from smoke outcomes.

Required:
- compile 0 errors / 0 warnings;
- `FINAL` lifecycle;
- opened = closed = CSV trade rows = path rows;
- zero invalid-price / invalid-risk / PnL-calc / path-calc failures;
- all required Trade Path fields present and parseable;
- exact source/output provenance.

## Development — frozen before D040 execution

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

Any failure => `REJECT_V0`. No post-hoc rescue and confirmation remains unopened.

## Confirmation — locked

Period: 2026-01-02 through 2026-06-30.
Symbols: all six.

This window remains unopened unless **every** frozen DEV gate passes.

Frozen confirmation gates:
- aggregate n >= 120;
- aggregate mean net R > 0;
- aggregate PF >= 1.08;
- at least 3/6 symbols positive;
- aggregate 1.5× commission-stress total net R > 0;
- zero integrity events.

Fail => `UNCONFIRMED`.

## Forbidden post-hoc changes

After D040 DEV results are seen, V0 may not be rescued by:
- changing strict `<` NR4 semantics or allowing ties;
- switching to NR5/NR6/NR7 or adding an inside-day requirement;
- changing the reference day or trigger range;
- removing ETH or any other symbol;
- deleting one direction;
- weekday/hour/session filters;
- RSI/EMA/ADX/ATR/volume/news/regime filters;
- stop/target/trailing/BE/partial tuning;
- changing development gates;
- opening 2026 confirmation after any DEV gate failure.

Any later hypothesis inspired by D040 must receive a new experiment ID and preregistration.
