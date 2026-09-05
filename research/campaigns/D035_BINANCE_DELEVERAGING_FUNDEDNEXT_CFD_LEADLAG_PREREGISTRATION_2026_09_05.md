# D035 — Binance BTC/ETH deleveraging shock -> FundedNext crypto CFD lead-lag

Date: 2026-09-05 Europe/Paris
Status: **PREREGISTERED / DEVELOPMENT DATA NOT YET INSPECTED**
Classification: **ADAPTATION_CROSS_VENUE_EVENT_STUDY**
Guardian: **OFF**
Orders: **NONE**

## Hypothesis

A sharp downside move on Binance BTCUSDT or ETHUSDT that is accompanied by a contemporaneous contraction in perpetual open interest can identify a deleveraging shock. The research question is whether other crypto CFDs on the target FundedNext feed incorporate that shock with a measurable delay.

This is not `OI down = short`. It is a cross-venue lead-lag event study: source event on Binance, response measured on independent target CFD quotes.

## Historical source data

Source assets: **BTCUSDT and ETHUSDT USD-M perpetuals only**.

Historical development inputs are frozen to official Binance Vision archives:
- 1-minute USD-M klines, resampled to an exact 5-minute source grid only when all five constituent minutes exist;
- daily `metrics` archives using `sum_open_interest` for the open-interest series.

No missing OI or price observation may be forward-filled. Duplicate/conflicting timestamps must be surfaced in QA and consolidated deterministically, never silently used twice.

The existing live Binance+Bybit EIB remains useful forward infrastructure, but its short accumulated history is not substituted for the historical development sample.

Historical liquidation data is **not** part of the D035 V0 gate because a clean, comparable exhaustive historical liquidation series is not presently frozen. Current/future EIB liquidation, funding, basis and cross-venue dislocation may be retained as diagnostics for later forward work but may not rescue or redefine V0 after results.

## Frozen development window

- Warm-up/download begins: **2023-11-01 UTC**.
- Development events: **2024-01-01 00:00 UTC through 2025-12-31 23:59 UTC**.
- Reserved untouched confirmation: **2026-01-01 through 2026-06-30 UTC**.

The analyzer must default to development mode and must not touch the 2026 confirmation window unless an explicit confirmation flag is used after a development PASS and a separate confirmation preregistration.

## Frozen source event

For each source asset independently on the 5-minute grid:

1. compute 5-minute perpetual close return;
2. compute 5-minute percentage change in `sum_open_interest`;
3. compute the rolling 30-day 10th percentile of each variable from **strictly prior observations only** (`shift(1)` before rolling quantile);
4. a downside deleveraging shock exists when:
   - current 5m return is negative and <= its prior rolling 10th percentile; and
   - current 5m OI change is negative and <= its prior rolling 10th percentile.

Minimum prior observations for a valid rolling threshold: **4000**.

Per-source cooldown: **30 minutes**. Keep the first qualifying event in the cascade; later qualifying observations inside the cooldown are not independent events.

BTC and ETH source events whose event timestamps are within **5 minutes** are merged into one event and tagged `BTCUSD+ETHUSD`. The earliest event timestamp is the merged event time.

No percentile, rolling window, cooldown, source direction or event merge interval may be changed after development results are inspected and still be called D035 V0.

## Target universe

Primary target universe is **all crypto CFDs actually available on the target FundedNext MT5 account and exported before D035 results are inspected**. BTCUSD is mandatory for server-time alignment. The user should export every available crypto CFD rather than select targets after seeing outcomes.

When exactly one source asset fires, that same asset's CFD is excluded from the primary cross-asset pool (for example BTC-only source -> BTCUSD is not a primary target). It can remain diagnostic. When BTC and ETH fire together, target rows remain tagged so source-asset responses can be separated from true non-source targets.

No unavailable symbol may be replaced after results by a different broker/feed.

## CFD quote export and clock alignment

The MT5 exporter records each observed tester minute's first and last BID/ASK and midpoint. It places no orders.

MT5 Strategy Tester server timestamps are **not assumed to be UTC**. Server->UTC alignment is a mechanical QA step, not a strategy parameter:
- derive 5-minute BTCUSD CFD midpoint returns;
- compare with Binance BTCUSDT contemporaneous 5-minute returns over integer offsets -8..+8 hours;
- calibrate by ISO week;
- require best correlation >= **0.75**, >= **100** paired observations, and a >= **0.10** correlation margin over the runner-up offset;
- exclude weeks failing this alignment gate.

A fixed offset may be supplied only as an explicit operational input and must still satisfy the correlation QA.

## Frozen target measurement

Source shock direction is downside. Primary executable test is therefore a **SHORT** on each eligible target:
- entry = first target **BID** at or after event time, maximum 2-minute tolerance;
- exit = first target **ASK** at or after each frozen horizon, maximum 2-minute tolerance;
- spread is therefore embedded.

Frozen horizons: **+1, +5, +15, +30, +60, +120 minutes**.
Primary horizon: **+15 minutes**.
Secondary persistence horizon: **+30 minutes**.

No SL, TP, trailing, Guardian management or synthetic R is invented at this stage.

## Matched control

For the +15m primary horizon, estimate a preregistered prior-history control from the preceding 60 days on the same target CFD:
- same weekday;
- same UTC hour;
- same 5-minute clock slot;
- exclude candidate control timestamps within +/-120 minutes of any known source event;
- require at least 8 valid controls;
- control statistic = median executable SHORT +15m return.

Primary differential = event executable SHORT +15m return minus matched-control median.

Control construction is diagnostic/statistical only; it is not an entry rule.

## Frozen development gates

D035 V0 passes development only if **all 8** gates pass:

1. >= **80** merged independent source events.
2. >= **2 non-source CFD targets** with >= **40** eligible +15m events each.
3. Pooled non-source mean executable SHORT return at +15m >= **+15 bps/event**.
4. Pooled mean event-minus-control differential at +15m >= **+10 bps/event**.
5. Day-cluster bootstrap 95% lower bound of pooled +15m differential > **0**.
6. Pooled executable SHORT return at +30m > **0**.
7. BTC-source-only and ETH-source-only pooled +15m differentials are both > **0**.
8. No single calendar month contributes > **35%** of total positive pooled +15m differential.

Failing development means **REJECT D035 V0**. Do not rescue with percentile mining, different horizons, a long-only inversion, a target shortlist, liquidation filters, RSI/ATR, funding, basis, OI-value thresholds, or source-specific thresholds on the inspected 2024-2025 sample.

Passing development means only `DISCOVERY_PASS_REQUIRES_2026_CONFIRMATION`. It does not authorize Guardian integration or live trading.

## Prepared artifacts

- MT5 quote exporter: `D035_CFD_M1_Exporter_v1_01.mq5`
  - local SHA-256 before repo commit: `2bd349d44845cbe726c154c5f419e2ec36763700dd245f2da6964bcb05342a96`
  - static balance QA passed; header/data row both 19 columns; MetaEditor compile not claimed.
- Historical analyzer: `D035_Binance_Deleveraging_LeadLag_v1_00.py`
  - local SHA-256 before repo commit: `fa22fa6a7fe735436b381ef2ec7a58f7aed8e71d526e2b679073a6981dfad133`
  - Python syntax compile passed; synthetic core smoke passed including source shocks, UTC+2 offset recovery, target joining, matched control and verdict plumbing.

## User run protocol

For the CFD export, use Strategy Tester on **BTCUSD plus every available FundedNext crypto CFD**, dates **2023-11-01 through 2025-12-31**, model **M1 / 1 minute OHLC**, no inputs changed. Zip the resulting `D035_CFD_M1_*.csv` files.

The Python analyzer downloads/caches the official Binance historical archives, performs clock QA and computes the frozen event study. The default invocation must remain development mode; do not use `--confirm` before a new confirmation preregistration.