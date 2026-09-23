# GUARDIAN — Filter Severity Audit

Date: 2026-09-23
Status: METHODOLOGY REVIEW / NO NEW RESEARCH RUN

Purpose:
Review whether Guardian repeatedly rejected small but potentially real effects because validation thresholds were calibrated for a large production edge rather than for detecting any reproducible mini-edge.

## Scope

This is a retrospective audit of documented verdict artifacts already present in the repository.
No new market-data run was launched.
No 2026 research sample was opened.

The audit distinguishes:
A. genuine negative / mechanism failures;
B. positive effects rejected mainly because they were below a large-edge magnitude threshold or failed an additional significance/robustness gate;
C. sparse/post-hoc cases where rejection was still clearly justified.

## Positive but rejected / not promoted

### D017 BTC SELL Momentum
Documented long-history pooled result:
- 2024 positive at larger targets;
- 2025 positive at larger targets;
- pooled EV2.5 about +0.131R;
- pooled EV3 about +0.125R;
- descriptive native management about +0.109R;
- 2024 descriptive comparator +0.112R;
- 2025 descriptive comparator +0.106R.

It was not promoted because the project required roughly +0.15R large-edge magnitude and realistic-cost cushion.

Audit classification:
POSITIVE_RECURRING_BELOW_LARGE_EDGE_HURDLE.

### D025 ETH RETEST
- 2024 EV2 +0.084R;
- 2025 EV2 +0.109R;
- Jun-Jul 2026 descriptive EV2 +0.588R;
- pooled 704 events, EV2 +0.133R before costs;
- Wilson interval for +2R hit probability above theoretical pre-cost break-even.

This was preserved as the strongest recurring path candidate rather than fully promoted.

Audit classification:
POSITIVE_RECURRING_MINI_EDGE_CANDIDATE.

### D025 GBP SHORT
Original 1.01 pooled 2024-2026:
- EV1 +0.121R;
- 2024 +0.070R;
- 2025 +0.183R;
- Jun-Jul 2026 +0.118R;
- Wilson-style EV interval roughly +0.022R to +0.217R.

Not promoted because it was below the project's large-edge standard and later 1.02 population weakened.

Audit classification:
POSITIVE_RECURRING_BUT_ESTIMATE_UNSTABLE.

### D025 EURUSD SHORT +2R
- 2024 EV2 about +0.146R;
- 2025 EV2 about +0.122R;
- pooled 2024-2025 EV2 about +0.136R;
- descriptive small 2026 sample supported direction;
- cluster uncertainty crossed zero.

Not promoted because it was slightly below +0.15R, uncertainty remained large and costs were not fully deducted.

Audit classification:
POSITIVE_RECURRING_NEAR_LARGE_EDGE_HURDLE.

### D030 ETH H4 Engulfing confirmation
Fresh PRE2024 confirmation:
- n=321;
- mean executable +0.0396R/trade;
- positive pooled mean;
- rejected because required >+0.15R, bootstrap lower >0, both directions positive, both temporal halves positive.

Cleaner no-gap subset was only about +0.0127R, so this is not strong evidence of a usable edge, but it is an example where "FAIL" did not mean negative.

Audit classification:
POSITIVE_BUT_WEAK_CONFIRMATION.

### D032 secondary management
Confirmed Doji entry remained valid, but the tested secondary management produced:
- +0.118R/event;
- bootstrap interval crossed zero.

Rejected because management advancement required >+0.15R plus positive bootstrap lower bound.

Audit classification:
POSITIVE_BUT_NOT_CONFIRMED_MANAGEMENT.

### D034 XAU abnormal-return
- n=83;
- mean executable +1.89 bps/event;
- median +8.45 bps;
- win rate 57.8%.

Rejected because hard economic hurdle was +15 bps/event and temporal/directional stability failed.

Audit classification:
POSITIVE_BUT_TOO_SMALL_AND_UNSTABLE.

### D035-E1 causal dual-source XLM
- n=870 primary rows;
- mean executable +15m +6.705 bps;
- raw bootstrap lower bound >0;
- differential +13.49 bps;
- differential bootstrap lower >0;
- +30m positive;
- both 2024 and 2025 positive.

Rejected mainly because frozen primary economic hurdle required >=15 bps executable mean and median >0.

Audit classification:
STATISTICALLY_SUPPORTED_POSITIVE_EFFECT_BELOW_LARGE_EDGE_HURDLE.

### M04 GBPUSD L15 validation
2018-2022:
- mean endpoint +0.06355;
- p_one 0.053625;
- rejected by p<=0.05 mechanical gate.

Audit classification:
POSITIVE_NEAR_SIGNIFICANCE_CUTOFF.

### M04 AUDUSD L15 locked OOS
2023-2025:
- n=1,467 / 612 days;
- mean endpoint +0.06973;
- p_one 0.103388;
- 2023 positive;
- 2024 positive;
- 2025 negative;
- all leave-one-year-out means positive.

Rejected by frozen p<=0.05 locked-OOS rule; diagnostics also show tail sensitivity and deterioration in 2025.

Audit classification:
POSITIVE_OOS_EFFECT_NOT_STATISTICALLY_CONFIRMED.

## Genuine rejects / not examples of excessive strictness

### D023 USDJPY London ORB
Although 2024-2026 clue was about +0.118R/trade after approximate commission, untouched 2023 confirmation was strongly negative:
- mean net -0.198R/trade;
- PF 0.708;
- bootstrap lower negative.
This is a genuine non-confirmation, not merely a threshold casualty.

### D029 TSMOM
- pooled executable mean -6.93 bps;
- later temporal half negative;
- bootstrap crossed zero.
Genuine reject.

### D033 double top/bottom
- mean -0.817R/trade;
- median -1.416R;
- both directions negative.
Genuine reject.

### D035 broad deleveraging
- executable pooled +15m SHORT -25.45 bps.
Genuine broad-strategy reject despite a small positive event-control differential.

### D036 Donchian
After removing two impossible-price synthetic winners:
- total -104.37R;
- mean -0.038R/trade;
- PF ~0.934.
Genuine reject.

### M04 EURUSD locked OOS
- mean endpoint -0.0457.
Genuine locked-OOS failure.

## Main conclusion

Guardian was NOT simply rejecting everything because of statistical rigor.
Many strategies genuinely turned negative on cleaner or fresher samples.

However, the repository contains multiple documented cases where a positive and sometimes recurring effect was not promoted because the project demanded a large edge, e.g. approximately +0.15R/trade or +15 bps/event, plus additional robustness/significance gates.

That methodology is appropriate for finding a standalone production strategy with a large cost cushion.
It is too severe if the research objective is instead:
"find any reproducible mini-edge that can later be combined with other independent signals."

The most important distinction going forward is:

1. EDGE EXISTENCE:
Does a small positive effect reproduce out of sample with plausible causal semantics?

2. STANDALONE TRADABILITY:
Is the effect large enough after costs to trade alone?

3. PORTFOLIO / ENSEMBLE VALUE:
Does the mini-edge add independent predictive information when combined with other signals?

These must no longer be collapsed into one pass/fail gate.

## Recommended new doctrine

Discovery:
- control multiplicity/data snooping strongly.

Fresh replication:
- require same direction and minimum support;
- estimate effect size and uncertainty;
- do NOT require +0.15R simply to call an effect real.

Validation / locked OOS:
- preserve fresh effect estimate;
- distinguish NEGATIVE, POSITIVE_UNCERTAIN, and POSITIVE_CONFIRMED;
- avoid repeated p<0.05 death gates.

Economic promotion:
- apply costs and production hurdles separately.
- a +0.03R to +0.10R repeatable effect may be retained as a component/covariate even if not standalone production-ready.

## Historical candidates worth reclassifying as mini-edge evidence, without retroactively declaring them production edges

High interest:
- D017 BTC SELL Momentum;
- D025 ETH RETEST;
- D025 EURUSD SHORT +2R;
- D035-E1 causal dual-source response;
- M04 AUDUSD recoupling as weak OOS-positive covariate evidence.

Medium/watch:
- D025 GBP SHORT;
- D030 ETH confirmation weak positive;
- D032 management positive but uncertain;
- D034 XAU tiny positive;
- M04 GBPUSD L15 near-significance validation.

No retroactive parameter tuning is authorized by this audit.
