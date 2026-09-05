# D032-C1 — Bullish Doji Star H1 core confirmation verdict

Date: 2026-09-05
Status: PRIMARY CONFIRMATION GATE PASS / SECONDARY -1R+3R MANAGEMENT NOT CONFIRMED
Classification: CONFIRMATION_CLOSE_REPLICATION_CFD_TRANSFER

Canonical preregistration: `research/campaigns/D032_C1_DOJI_STAR_H1_CONFIRMATION_PREREGISTRATION_2026_09_05.md`

## Important execution limitation
FundedNext historical M1 bars are available pre-2024, but historical real ticks are not. The confirmation runs therefore used `1 minute OHLC` rather than `Every tick based on real ticks` for the pre-2024 window.

This is acceptable for the **primary +24h endpoint** because the signal is H1 and the primary result is the executable entry-to-24h return. It is not sufficient to claim exact intraminute first-touch validation for the secondary -1R/+3R management rule.

Commission input was 0 bps/side. Executable ASK entry / BID exit embeds the tester spread model, but explicit commission stress remains required before production.

## Frozen core cohort results
Clean sample = `feed_gap=0`, `missing_horizons=0`, valid executable +24h return.

| Symbol | Clean n | Mean +24h | Median +24h | Win rate | Mean +24h R | Same-trend control mean | Doji-control diff |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | 33 | +139.46 bps | +139.56 bps | 69.70% | +1.111R | +30.03 bps | +109.43 bps |
| ETHUSD | 32 | +76.43 bps | +71.56 bps | 62.50% | +0.043R | +42.90 bps | +33.53 bps |
| DOGUSD | 14 | +249.98 bps | +81.36 bps | 57.14% | +0.599R | +19.80 bps | +230.19 bps |

DOGUSD broker history for this run begins 2021-09-24, so its confirmation window is shorter than BTC/ETH.

## Aggregate core result
BTC+ETH+DOG clean aggregate:
- n = 79 clean events;
- mean executable +24h = **+133.52 bps/event**;
- median executable +24h = **+93.43 bps/event**;
- win rate = **64.56%**;
- mean source-risk-normalized result = **+0.588R/event**;
- pooled same-trend control mean = **+32.13 bps**;
- aggregate Doji-control differential = **+101.38 bps/event**.

The full diagnostic response curve remains positive and generally strengthens toward 24h in the pooled confirmation sample:
`1h +4.38`, `2h +4.95`, `3h +24.87`, `6h +13.12`, `9h +28.34`, `12h +50.39`, `15h +81.76`, `18h +108.16`, `24h +133.52 bps`.

Month-block bootstrap of the pooled +24h executable mean (33 calendar-month blocks, 20,000 resamples) gives an approximate 95% interval of **+10.1 to +273.4 bps**. The lower bound remains above zero.

## Preregistered primary gate
1. >=50 clean core events: **PASS** (79).
2. Aggregate mean net executable +24h > 0: **PASS** (+133.52 bps with explicit commission input 0).
3. Aggregate mean +24h > +0.15R/event: **PASS** (+0.588R).
4. Month-block bootstrap 95% lower bound > 0: **PASS** (~+10.1 bps).
5. At least 2/3 core symbols positive: **PASS** (3/3 positive in mean bps).
6. Aggregate Doji minus same-trend control differential > 0: **PASS** (+101.38 bps).
7. No single core symbol contributes >60% of pooled positive net result: **PASS**. Net contribution shares are approximately BTC 43.6%, ETH 23.2%, DOG 33.2%.

**Formal primary verdict: PASS. The Bullish Doji Star H1 entry edge is confirmed under the preregistered pre-2024 core gate on this CFD feed, subject to the execution/data-quality limitations below.**

## Stability caveats
The confirmation is not perfectly uniform through time.

Pooled yearly executable +24h means:
- 2020: +113.3 bps (17 events)
- 2021: +316.0 bps (20)
- 2022: +85.7 bps (24)
- 2023: +13.6 bps (18)

ETH specifically weakens materially in the later years: 2022 mean about -172.4 bps and 2023 about -98.1 bps, while BTC remains positive. DOG has only 14 clean events and no clean 2023 event in this run. Therefore the entry passes the frozen gate, but regime/market stability still needs monitoring before production sizing.

## Secondary -1R / +3R / 24h management hypothesis
Pooled core clean result:
- mean secondary management = **+0.118R/event**;
- first outcomes: 48 stop-first, 16 target-first, 15 timeout;
- month-block bootstrap approximate 95% interval = **-0.274R to +0.525R**.

The preregistered management gate required >+0.15R/event, bootstrap lower bound >0, and at least 2/3 core symbols positive. The first two fail. In addition, these runs used 1-minute OHLC rather than historical real ticks, so exact intraminute first-touch ordering is not fully authoritative.

**Secondary management verdict: NOT CONFIRMED. Do not adopt -1R/+3R as the production management rule.**

## Additional non-core transport observation
User also supplied an ADAUSD run, which was not in the preregistered core or transport list. Treat it as an external diagnostic only:
- clean n = 16;
- mean +24h = -108.64 bps;
- win rate = 25%;
- mean +24h = -0.796R;
- same-trend control mean = +8.81 bps;
- Doji-control differential = -117.45 bps.

ADA is a strong counterexample to any claim that the setup is universally valid across crypto CFDs.

## Decision
- **ENTRY EDGE: CONFIRMED under D032-C1 primary gate.**
- **SECONDARY -1R/+3R MANAGEMENT: NOT CONFIRMED.**
- Do not tune the pattern/trend definition on this confirmation sample.
- Next strategy work should preserve the confirmed 24h reference while designing management in a separate, preregistered experiment.
- Because signal frequency is low, continue independent research for a substantially more active challenge engine rather than expecting this setup alone to complete a prop-firm challenge quickly.
- Before Guardian integration, perform explicit cost stress and standalone portfolio overlap/risk analysis.
