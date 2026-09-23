# D035-E1 — Multi-asset portfolio drawdown audit

Date: 2026-09-23
Source: original returned `D35 CASUAL.zip`, event-level `D035_E1_EVENT_TARGET_RETURNS.csv`
Status: READ-ONLY PORTFOLIO AUDIT / NO NEW MARKET DATA / NO RETUNING

## Scope

Same causal D035-E1 event timestamps, +15m executable SHORT returns with BID entry / ASK exit.

Audited assets:
- BTCUSD
- ETHUSD
- XLMUSD

Portfolio convention:
- equal notional weights across selected assets;
- portfolio return in bps = arithmetic mean of constituent event returns;
- therefore "1.0x gross" means total gross notional equals equity, split equally across portfolio assets;
- all portfolio results use the 870 events where BTC, ETH and XLM are simultaneously available.

This is a retrospective portfolio construction on already-inspected 2024-2025 data. It is not independent confirmation.

## Single-asset event statistics

BTCUSD:
- mean +10.371 bps/event
- median +6.437
- win rate 57.36%
- cumulative simple +9023.09 bps
- max cumulative drawdown -757.82 bps
- worst event -325.45 bps

ETHUSD:
- mean +15.017 bps/event
- median +8.333
- win rate 57.13%
- cumulative simple +13065.03 bps
- max cumulative drawdown -1058.54 bps
- worst event -481.78 bps

XLMUSD:
- mean +6.705 bps/event
- median 0.000
- win rate 49.43%
- cumulative simple +5833.12 bps
- max cumulative drawdown -2108.42 bps
- worst event -544.93 bps

## Correlation

Event-return correlations:
- BTC / ETH: 0.8400
- BTC / XLM: 0.7520
- ETH / XLM: 0.7970

Therefore XLM is not a strong diversifier for this event family.

## Equal-weight BTC + ETH

- n = 870
- mean +12.694 bps/event
- median +7.382
- win rate 58.28%
- cumulative simple +11044.06 bps
- max cumulative DD -908.18 bps
- worst event -403.62 bps
- max consecutive losing events: 7
- worst Prague-calendar-day aggregate: -277.10 bps

Compounded illustrations under constant total gross exposure:
- 0.25x gross: final +31.64%, max DD -2.25%
- 0.33x gross: final +43.68%, max DD -2.97%
- 0.40x gross: final +55.08%, max DD -3.59%
- 0.50x gross: final +72.90%, max DD -4.47%
- 1.00x gross: final +196.17%, max DD -8.82%

These compounded figures are historical mechanical illustrations, not forecasts.

## Equal-weight BTC + ETH + XLM

- n = 870
- mean +10.698 bps/event
- median +6.304
- win rate 56.44%
- cumulative simple +9307.08 bps
- max cumulative DD -924.55 bps
- worst event -450.72 bps
- max consecutive losing events: 11
- worst Prague-calendar-day aggregate: -349.59 bps

Compounded illustrations:
- 0.25x gross: final +26.04%, max DD -2.30%
- 0.33x gross: final +35.66%, max DD -3.02%
- 0.40x gross: final +44.64%, max DD -3.66%
- 0.50x gross: final +58.46%, max DD -4.56%
- 1.00x gross: final +148.60%, max DD -8.99%

## Portfolio conclusion

On the existing D035-E1 ledger, adding XLM to BTC+ETH:
- lowers mean event return from +12.694 to +10.698 bps;
- slightly worsens max DD from -908.18 to -924.55 bps;
- worsens worst daily aggregate from -277.10 to -349.59 bps;
- increases the longest losing run from 7 to 11 events.

Therefore the cleanest historical multi-asset implementation is BTC+ETH equal-weight, not BTC+ETH+XLM.

This does NOT mean XLM has no signal. XLM remains a positive cross-asset response. It means that in the same-event portfolio it does not improve diversification enough to compensate for its weaker standalone return and larger drawdown.

## Scientific status

BTC and ETH were diagnostic source-asset rows in D035-E1, not the preregistered primary target. A BTC+ETH production basket is therefore a new portfolio hypothesis built from same-sample diagnostics.

Use this audit to prioritize forward simulation / fresh transport testing, not to relabel the historical evidence as independent confirmation.
