# D030-C1 — ETHUSD H4 Alanazi Engulfing PRE2024 confirmation verdict

Date: 2026-09-05
Status: **FAIL / REJECT ETH TRANSPORT CONFIRMATION**
Classification: `POSTHOC_SYMBOL_SELECTION / CFD_TRANSPORT_CONFIRMATION`

Preregistration: `research/campaigns/D030_C1_ETHUSD_H4_ENGULFING_TRANSPORT_CONFIRMATION_PREREGISTRATION_2026_09_05.md`
Preregistration commit: `495ceda0ab53857ce768cf391c49489a067017dc`

## Inputs received
User supplied the unchanged D030 v1.01 ETHUSD run over the PRE2024 confirmation interval.

Run metadata:
- symbol: ETHUSD
- first tester tick: 2019-01-01 23:00
- last tester tick: 2024-01-01 23:59:59
- eligible signal window: 2019-01-01 through 2023-12-31
- completed eligible events: 321
- spread embedded via BID/ASK
- historical swap not included
- tester model: M1 / `1 minute OHLC`
- no Guardian / no orders

## Primary results
Across all 321 eligible events:
- wins: 163
- losses: 158
- win rate: 50.779%
- mean binary 1:1 outcome: +0.015576R
- mean executable realized result: **+0.039619R/trade**
- median executable result: about +1.0016R
- total scanner pip result: **-57,603 pips**
- mean scanner pip result: -179.449 pips/trade
- average duration: 30.136 h
- average MFE: +0.808835R
- average MAE: -0.776161R

The executable mean is positive but far below the preregistered +0.15R threshold.

## Direction robustness
- LONG: n=136, mean **-0.025722R**, win rate 48.53%
- SHORT: n=185, mean **+0.087654R**, win rate 52.43%

The frozen requirement that both directions be positive fails.

## Temporal robustness
- 2019-2021: n=146, mean **-0.002493R**
- 2022-2023: n=175, mean **+0.074753R**

The frozen requirement that both temporal halves be positive fails.

Year detail:
- 2019: n=7, +0.227411R
- 2020: n=73, +0.065086R
- 2021: n=66, -0.101624R
- 2022: n=84, -0.002717R
- 2023: n=91, +0.146264R

## Month-block bootstrap
53 calendar months containing events were resampled as blocks, 20,000 resamples.

Approximate 95% interval for mean executable R:
- lower: **-0.0845R**
- median: +0.0397R
- upper: +0.1676R

The lower bound is below zero, so the frozen bootstrap gate fails.

## Concentration
Total positive executable R ≈ 194.227R.
Largest single positive event ≈ 5.565R, or **2.86%** of total positive R.

The <=10% concentration gate passes.

## Data-quality diagnostic
51 / 321 events are flagged `feed_gap_after_entry=1`.
- no-gap events: n=270, mean executable result ≈ **+0.01268R**
- gap-flagged events: n=51, mean ≈ **+0.18224R**

Thus the already-small positive mean is not improved by excluding gap-affected events; on the cleaner subset it is essentially flat. This is diagnostic only because the preregistered primary gate used the unchanged scanner output, but it strengthens the rejection rather than rescuing the strategy.

## Frozen gate verdict
1. >=250 completed eligible trades: **PASS** (321)
2. mean executable R > +0.15R/trade: **FAIL** (+0.0396R)
3. month-block bootstrap 95% lower bound >0: **FAIL** (~-0.0845R)
4. LONG and SHORT means both >0: **FAIL** (LONG negative)
5. 2019-2021 and 2022-2023 means both >0: **FAIL** (2019-2021 slightly negative)
6. no single event >10% of positive R: **PASS** (~2.86%)

**Final: 2/6 gates pass. D030-C1 ETH transport confirmation FAILS.**

## Decision lock
Reject ETHUSD H4 Alanazi Engulfing as a confirmed transport edge in this exact form. Do not tune trend filters, direction, RR, candle size, session, or stop distance on the same confirmation interval.

The 2024-2026 ETH discovery result (~+0.161R/trade) is not stable across the independent earlier interval. Historical swap stress is unnecessary as an advancement step because the pre-swap confirmation already fails.
