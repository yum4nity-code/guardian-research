# D032-C1 — Bullish Doji Star H1 — BTC confirmation partial

Date: 2026-09-05
Status: PARTIAL CONFIRMATION / BTC ONLY
Experiment: `D032_C1_CONFIRM_DojiStar_H1`
Feed: FundedNext BTCUSD CFD
Tester: M1, `1 minute OHLC`
Requested period: 2018-07-01 to 2024-01-01
Frozen signal window: 2018-07-01 through 2023-12-30 23:00 server time
Important tester note: analyzed-history quality reported by MT5 = 63%; historical real ticks are unavailable for this period, so this run is suitable for the primary +24h bar-based confirmation endpoint but NOT definitive first-touch validation.

## Primary BTC confirmation result

The scanner detected 42 Bullish Doji Star confirmation signals. Nine were excluded from the clean +24h cohort because of feed gaps / missing exact horizons, leaving 33 clean events.

For those 33 clean BTC events:
- executable CFD mean return at +24h: **+139.46 bps** (+1.3946%)
- median executable return at +24h: **+139.56 bps**
- executable +24h win rate: **69.70%**
- mean +24h return in source-defined risk units: **+1.111R/event**
- source-close mean at +24h: about **+140.09 bps**
- executable minus source-close mean difference: about **-0.63 bps**, so the bar-level executable layer preserved the +24h effect in this BTC run.

Simple event bootstrap of the 33 clean +24h returns gives an approximate 95% mean interval of about **+30 to +258 bps**. Treat this as descriptive because events are not guaranteed IID and history quality is imperfect.

## Year stability, clean BTC events

- 2020: n=9, mean +19.35 bps, median +25.31 bps
- 2021: n=10, mean +245.59 bps, median +280.21 bps
- 2022: n=5, mean +168.96 bps, median +170.90 bps
- 2023: n=9, mean +125.26 bps, median +106.22 bps

All represented clean years are positive on the raw +24h endpoint, although 2020 is weak.

## Same-downtrend control

Clean same-downtrend/no-Doji controls: n=7,773.
- mean executable +24h return: about **+30.03 bps**
- median: about +27.50 bps
- win rate: about 55.01%

BTC Doji incremental mean versus this broad control is therefore about **+109.43 bps** at +24h. This is encouraging but not a formal matched causal estimate; controls are serially dependent and the tester history is only 63% quality.

By year, 2020 Doji mean (+19.35 bps) is actually below the broad control mean (+31.95 bps), while 2021-2023 Doji means are materially above controls. Do not hide this 2020 weakness.

## Horizon response

Clean event mean executable returns:
- +1h: +1.27 bps
- +2h: -4.29 bps
- +3h: +14.00 bps
- +6h: -22.40 bps
- +9h: -27.42 bps
- +12h: -36.73 bps
- +15h: +32.31 bps
- +18h: +37.99 bps
- +24h: +139.46 bps

This differs from the 2024-2026 discovery sample, where the pooled response appeared to strengthen more progressively. On BTC 2018-2023 the confirmation edge is concentrated late, especially by +24h. Preserve +24h as the primary endpoint; do not optimize a new shorter horizon from this run.

## Frozen secondary management hypothesis: -1R / +3R / timeout 24h

On the 33 clean BTC events, generated-M1 first-touch accounting gives:
- stop first: 20
- +3R target first: 6
- 24h timeout: 7
- mean management result: approximately **+0.003R/event** before any reliable real-tick reconstruction
- median management result: approximately -1.03R

Therefore the `-1R / +3R / 24h` management hypothesis is **NOT confirmed on BTC**. More importantly, this period has no historical real ticks; M1 OHLC generated ticks are not adequate for a definitive first-touch verdict. The primary +24h endpoint and the management hypothesis must remain separate.

## Current interpretation

BTC materially strengthens the hypothesis that Bullish Doji Star H1 contains +24h information on the target CFD feed. The discovery BTC 2024-2026 mean was about +50.7 bps; this untouched historical BTC cohort produces +139.5 bps on 33 clean events. This is a genuine encouraging confirmation signal, but it is still only one of the three frozen core markets and uses imperfect 63%-quality historical bars.

Do not promote the strategy to Guardian/production from BTC alone. Complete ETH and DOGE core confirmation first; LINK and XRP remain transport diagnostics. Do not tune the pattern, trend filter or exit horizon after this BTC result.
