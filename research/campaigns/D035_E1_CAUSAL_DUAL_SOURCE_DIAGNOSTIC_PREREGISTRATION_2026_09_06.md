# D035-E1 — causal BTC+ETH dual-source confirmation diagnostic

Date: 2026-09-06 Europe/Paris
Status: **PREREGISTERED EXPLORATORY SAME-SAMPLE DIAGNOSTIC / NOT CONFIRMATION**

Parent campaign: D035 Binance BTC/ETH deleveraging -> FundedNext crypto CFD lead-lag.
Parent primary verdict: **DISCOVERY_REJECT 4/8**.

## Why this exists

A post-hoc split of D035 development rows labelled `BTCUSD+ETHUSD` looked much stronger than the frozen broad D035 result. Code audit showed that this subgroup cannot be interpreted causally from the existing output: the D035 merge routine keeps the timestamp of the first source shock while adding the second source to the group label if it arrives within five minutes.

Therefore any strategy that conditions on `BTCUSD+ETHUSD` must wait until the second/opposite source shock is actually observable.

D035-E1 is a new exploratory diagnostic on the already inspected 2024-2025 development sample. It cannot rescue the rejected D035 primary and cannot be called independent validation.

## Frozen E1 event rule

Source data and single-source shock definitions remain exactly those frozen in D035:
- Binance Vision USD-M BTCUSDT and ETHUSDT;
- 5m perpetual return <= strictly-prior rolling 30d 10th percentile and negative;
- 5m `sum_open_interest` change <= strictly-prior rolling 30d 10th percentile and negative;
- same 30-minute per-source cooldown.

Dual-source event:
1. first qualifying BTC or ETH shock starts a five-minute window;
2. the opposite source must also qualify within <=5 minutes;
3. **signal timestamp = later/second qualifying source event**;
4. if the opposite source does not qualify within five minutes, there is no E1 event.

No future source label may be known at the signal timestamp.

## Sample

Exploratory development only: **2024-01-01 through 2025-12-31 UTC**.
Warmup unchanged from D035.

Reserved **2026-01-01 through 2026-06-30 remains untouched** by E1.

## Targets

Primary cross-asset target frozen before E1 execution: **XLMUSD**.
Reason for choosing it is explicitly post-hoc: in the invalid/early-timestamp dual-source development split it was the only non-source CFD with mean executable +15m above the original +15 bps economic hurdle. This selection is discovery, not validation.

All other available FundedNext crypto CFDs are diagnostics only and cannot substitute for XLMUSD in the E1 advancement gate.

## Execution / response

- executable SHORT entry at first available FundedNext CFD BID at/after the causal second-source timestamp;
- executable exits use ASK;
- primary horizon +15m;
- frozen diagnostics +1/+5/+30/+60/+120m;
- prior-only causal control unchanged from D035 and excludes windows around all original D035 source shocks;
- no SL/TP/Guardian/order simulation.

## Frozen E1 advancement gate — XLMUSD

All 8 required:
1. >=200 causal dual-source events with executable +15m XLMUSD response;
2. mean executable SHORT +15m >= +15 bps;
3. median executable SHORT +15m > 0;
4. day-cluster bootstrap 95% lower bound of raw executable +15m > 0;
5. mean event-minus-causal-control +15m >= +10 bps;
6. day-cluster bootstrap 95% lower bound of +15m differential > 0;
7. mean executable SHORT +30m > 0;
8. mean executable SHORT +15m > 0 in both 2024 and 2025.

Only 8/8 permits a **fresh D035-C1 preregistration before opening 2026-H1**.

## Prohibited after E1 is run

Do not same-sample rescue by changing:
- five-minute dual-source window;
- source percentiles/lookback/cooldown;
- target from XLMUSD to another winner;
- +15m primary horizon;
- direction;
- adding liquidation/funding/basis/RSI/ATR filters.

If E1 fails, close this causal dual-source branch unless a genuinely new independent dataset or mechanism justifies another separately labelled discovery campaign.