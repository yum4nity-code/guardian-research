# R21-R25 Discovery Freeze — 2026-09-16

## Scope

This document freezes the R21-R25 XAUUSD discovery-stage interpretation before any
R21 confirmation payload (2019-07-01 through 2024-12-31) is opened.

Discovery source:
- engine: xau_edge_discovery_r21_r25_v1_03.py
- orchestrator job: R21-R25-XAU-DISCOVERY r6
- source commit: e95d4188370a8e4a6ae945d1319ae8389ea3316b
- run status: PASS
- owner-supplied SUMMARY.json SHA256:
  74f597f767f8c4dbe2cb7ca84a6cbb54d535e1f80effdd5641db9da05486e5c8
- discovery rows: 1,100,160 M5
- source days: 3,820
- discovery window: 2004-11-08 through 2019-06-30
- 2025 remained unopened
- 2026+ remained unopened

No parameter rescue is permitted after this freeze.

## R21 — COMEX 15-minute unconditional drift

Frozen primary metric: post_15m.

Discovery:
- n / clustered days: 3,820
- mean: +0.0001111702926410998
- day-clustered t: +2.8805394619816034
- positive years: 12
- negative years: 4
- sign consistency: 0.75

Descriptive only:
- post_30m mean +0.000048376845558849466; t +1.0274230186719266
- post_60m mean +0.000036807386137202245; t +0.6000645789588245
- post_120m mean -0.000038525483940168993; t -0.43181150403663454

Decision:
- SURVIVES discovery.
- Only R21 is promoted from this batch to independent confirmation.
- Confirmation hypothesis remains exactly: positive unconditional return from the
  08:20 America/New_York M5 close anchor to 15 minutes later.

Frozen confirmation gate:
- post_15m mean > 0
- post_15m day-clustered t > +2.0
- yearly stability is descriptive only and is not an additional gate
- 30m / 60m / 120m remain descriptive and cannot rescue a failed 15m primary

No weekday, session, news, volatility, direction, magnitude or other filter may be
introduced.

## R22 — volatility compression -> expansion

Primary state: bottom10.
Primary horizons: 4b and 8b.

Discovery bottom10:
- excess_abs_4b mean -0.00015638882587303937; complete-estimator day-jackknife
  t -18.92675989606528; 3 positive / 13 negative years
- excess_abs_8b mean -0.00020790988129736705; complete-estimator day-jackknife
  t -17.74653252800569; 2 positive / 14 negative years

Secondary bottom20 is also negative:
- excess_abs_4b mean -0.00012723082083150442; t -20.96027418025656
- excess_abs_8b mean -0.00016261319676319887; t -18.13089524245364

Decision:
- FAIL discovery under the preregistered expansion hypothesis.
- The strong inverse effect is scientifically notable but cannot be sign-flipped
  into a success inside R22.
- Any compression-persistence hypothesis must be a new separately preregistered
  study.

## R23 — overnight move -> New York continuation/reversal

Primary horizons: 30m and 60m.

Discovery continuation:
- 30m mean +0.0000564107046966505; t +1.1909124225989551;
  8 positive / 8 negative years
- 60m mean +0.00006798386797580214; t +1.1018368922518649;
  9 positive / 7 negative years

Reversal is the exact sign mirror and is not significant.

Decision:
- FAIL / not promoted.
- No magnitude bucket, weekday or session rescue.

## R24 — COMEX opening-range breakout

Preregistered primary sign: continuation.
Primary horizons: 2b and 4b.

Discovery continuation:
- 2b mean -0.00004904292813144948; t -1.8977738256000094;
  8 positive / 8 negative years
- 4b mean -0.00008173435133260174; t -2.2952902975103644;
  5 positive / 11 negative years

The symmetric reversal statistic is positive:
- reversal_4b mean +0.00008173435133260174; t +2.2952902975103644
- reversal_8b mean +0.00012886812429148252; t +2.6579003551869067
- reversal_16b mean +0.00023675530664637502; t +3.1805857226220584

Decision:
- R24 continuation FAILS discovery.
- Reversal is not promoted by relabelling R24 after observing the result.
- It may motivate a new R26-style preregistered study before any independent
  confirmation data are opened for that new hypothesis.

## R25 — NY-open gap toward previous daily close

Primary horizons: 30m and 60m.

Discovery:
- toward_30m mean -0.00006739782330186336; t -1.423402441350675
- away_30m mean +0.00006739782330186336; t +1.423402441350675
- toward_60m mean -0.00007298612548548910; t -1.1831893679276562
- away_60m mean +0.00007298612548548910; t +1.1831893679276562
- yearly sign stability at the 30m primary pair: 8 / 8

Descriptive fill probabilities:
- 15m: 0.21511321748288573
- 30m: 0.2646129541864139
- 60m: 0.3341232227488152
- 120m: 0.4410215903106898

Decision:
- FAIL / not promoted.
- No gap-size threshold may be introduced as a rescue.

## Frozen survivor set

Promoted to confirmation:
1. R21 COMEX 15-minute unconditional drift

Not promoted:
- R22
- R23
- R24
- R25

Potential future separately-preregistered research ideas:
- R22 inverse / compression persistence
- R24 opening-range reversal

These ideas are explicitly not confirmation survivors and must not reuse the
R21 confirmation run as an opportunistic test.

## Confirmation doctrine

R21 confirmation window is frozen:
- start: 2019-07-01
- end: 2024-12-31

Before opening confirmation:
- confirmation-only code must be reviewed independently
- exact R15 index/path/SHA provenance remains pinned
- builder must physically open only confirmation payload bytes
- 2025 must remain physically unopened
- 2026+ must remain hard sealed
- R21 event extractor must reuse the frozen discovery definition
- primary metric and gate above must be encoded before execution

A failed R21 confirmation ends R21 in this research branch. No parameter, horizon,
filter, anchor or sign change may rescue it.
