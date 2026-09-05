# D032-C1 — XRP transport result

Date: 2026-09-05
Status: TRANSPORT FAIL / DOES NOT ALTER CORE PASS
Experiment: `D032_C1_CONFIRM_DojiStar_H1`
Feed: FundedNext XRPUSD CFD
Cohort: `TRANSPORT_XRP`
Tester: M1, `1 minute OHLC`
Frozen confirmation window: 2018-07-01 through 2023-12-30 23:00 server time

## Result
The scanner accepted 52 Bullish Doji Star signals. Fourteen were excluded from the clean +24h cohort because of feed gaps / missing exact horizons, leaving 38 clean events.

Clean XRP result:
- mean executable +24h = **-200.11 bps** (-2.0011%)
- median executable +24h = **-43.25 bps**
- win rate = **47.37%**
- mean +24h in source-risk units = **-0.535R/event**
- same-downtrend/no-Doji clean controls n = 8,919
- same-downtrend control mean +24h = **+15.25 bps**
- Doji minus control differential = **-215.35 bps/event**

Approximate event bootstrap 95% interval for the mean: about -531 to +84 bps. Month-block bootstrap: about -483 to +42 bps. Both include zero and center materially negative.

## Time stability
Clean yearly mean +24h:
- 2020: -257.8 bps (n=16)
- 2021: -230.4 bps (n=8)
- 2022: -129.3 bps (n=7)
- 2023: -104.4 bps (n=7)

All represented years have negative mean +24h return.

## Horizon profile
Mean executable return by horizon on the 38 clean events:
- 1h: -24.6 bps
- 2h: -54.9 bps
- 3h: -70.0 bps
- 6h: -98.2 bps
- 9h: -175.4 bps
- 12h: -176.3 bps
- 15h: -209.5 bps
- 18h: -249.9 bps
- 24h: -200.1 bps

The adverse drift is broad across the horizon ladder, not a single 24h outlier.

## Secondary management
Frozen secondary -1R/+3R/24h hypothesis:
- mean management = **-0.570R/event**
- stop first = 29
- target first = 4
- timeout = 5

This is a clear fail. Historical real ticks are unavailable, so first-touch precision remains limited, but the primary +24h result already rejects XRP transport.

## Decision
**XRP transport: FAIL.**

This does not alter the preregistered BTC/ETH/DOGE core confirmation PASS. Together with LINK and ADA, XRP is strong evidence that the Bullish Doji Star H1 effect is not universal across crypto CFDs. The setup should therefore be treated as a market-specific validated sleeve for the confirmed core cohort, not as a generic all-crypto rule.
