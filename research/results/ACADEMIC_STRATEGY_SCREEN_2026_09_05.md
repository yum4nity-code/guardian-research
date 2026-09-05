# Academic Strategy Screen — 2026-09-05

Status: EVIDENCE-FIRST SCREEN / NO POST-HOC PARAMETER SEARCH

## Purpose

The current reset is not to invent more indicator combinations. It is to search for systematic families with credible published evidence, distinguish what is directly replicated from what is merely inspired by the literature, and kill unsuitable ideas before coding them.

The user's production preference remains a materially large, recurring edge rather than tiny statistically significant anomalies.

## Screened family 1 — broad FX technical trading literature

### Hsu, Taylor & Wang (2016), Journal of International Economics
DOI: 10.1016/j.jinteco.2016.03.012

Published evidence:
- 45 years of daily FX data;
- 30 developed and emerging currencies;
- more than 21,000 technical trading rules;
- explicit defenses against data-snooping bias;
- out-of-sample cross-validation;
- substantial predictability/profitability in some periods/currency groups;
- strong time-series and cross-sectional variation.

Interpretation for Guardian:
- this is strong evidence that systematic FX technical effects are not imaginary;
- it is equally strong evidence against expecting one universal fixed rule to dominate every currency and every regime;
- the paper searched very large rule families, so we must NOT cherry-pick its historical best parameter combination as our next EA;
- it supports our architecture of several independently validated sleeves with symbol eligibility, not one strategy forced across everything.

Decision: USE AS FAMILY-LEVEL EVIDENCE, NOT AS AN EXACT V0 REPLICATION.

## Screened family 2 — engulfing patterns in spot FX

### Alanazi (2020), European Journal of Finance
DOI: 10.1080/1351847X.2020.1748679

Published evidence visible from the publisher/abstract:
- bullish and bearish engulfing patterns in spot FX;
- 112,792 in-sample daily candles;
- 148,992 out-of-sample four-hour candles;
- more than 3 million spot quote observations;
- 24 currency pairs over 2000-2018;
- statistically significant profitability reported particularly for the seven majors;
- transaction costs are explicitly important.

Why this is interesting for us:
- direct FX evidence rather than transfer from equities;
- four-hour out-of-sample sample is much closer to a practical prop-firm cadence than daily patterns;
- a candlestick structure can be coded deterministically if the exact paper rules are recovered.

Current blocker:
- the accessible publisher page exposes the abstract but not enough detailed methodology to claim an exact faithful replication of entry, exit, stop and any trend/gap conventions.
- we will NOT invent missing rules and then call it a replication.

Decision: HIGH-INTEREST RESERVE CANDIDATE / DO NOT EXECUTE UNTIL EXACT METHODOLOGY IS VERIFIED.

## Screened family 3 — Piercing Line / Dark Cloud Cover in spot FX

### Alanazi, Alanazi & McMillan (2020), Cogent Economics & Finance
DOI: 10.1080/23322039.2020.1768648

Published evidence:
- 112,792 daily candles;
- more than one million spot quotes;
- 24 FX pairs, 2000-2018;
- authors report aggregate chart-pattern profitability exceeding 600% after transaction costs;
- transaction costs, especially spread, materially reduce profitability.

The open-access study is useful because it demonstrates that a very simple, visually recognizable price-action family can be specified and tested across many FX pairs.

Why it is NOT a primary challenge candidate today:
- the study's primary sample is daily candles;
- reported occurrence frequency per individual pair is therefore too low for the user's desired challenge cadence;
- using it as an H1/H4 strategy without a separate published basis would be a new adaptation and must be preregistered as such, not presented as the paper's result.

Decision: SOLID EVIDENCE FOR PRICE-ACTION RESEARCH, BUT DEFER AS A DIRECT CHALLENGE ENGINE DUE TO FREQUENCY.

## Screened family 4 — FX fixing reversal

### Krohn, Mueller & Whelan (2024), Journal of Finance
DOI: 10.1111/jofi.13306

Published evidence:
- top nine traded currencies;
- 21-year high-frequency sample;
- pervasive USD appreciation before major FX fixes and reversal afterward;
- natural-experiment evidence links the timing to published reference rates.

Critical implementation result from the paper:
- the unconditional reversal is economically real;
- however, for a trader accessing the client market, transaction-cost-adjusted returns to the simple reversal trade are significantly negative;
- positive economics are associated with liquidity provision/dealer intermediation instead.

Decision: SCREENED OUT FOR OUR RETAIL/PROP CFD EXECUTION. Do not spend code/backtest time trying to harvest an effect that the paper itself says is destroyed by client-market costs.

## Screened family 5 — classic time-series momentum / trend following

### Moskowitz, Ooi & Pedersen (2012), Journal of Financial Economics
DOI: 10.1016/j.jfineco.2011.11.003

Published evidence:
- 58 liquid equity-index, currency, commodity and bond futures;
- significant time-series momentum in every instrument considered;
- return persistence over roughly one to twelve months;
- diversified strategy abnormal returns with limited standard factor exposure.

### Hurst, Ooi & Pedersen (2017), Journal of Portfolio Management
DOI: 10.3905/jpm.2017.44.1.015

Published evidence:
- historical trend-following reconstruction back to 1880;
- positive average time-series-momentum returns in every decade in their study;
- performance across varied macroeconomic environments and many major crisis periods.

Interpretation for Guardian:
- D017's failure does NOT reject trend following as a family; D017 was an intraday impulse/continuation engine with multiple filters, not literature-style slow TSMOM;
- this is probably the strongest external evidence base in the current slate;
- downside is cadence: it is too slow to be the main challenge-finishing engine.

Decision: KEEP D029 AS A SANITY BENCHMARK / DIVERSIFIER, NOT PRIMARY FAST ENGINE.

## Screened family 6 — Opening Range Breakout

### Holmberg, Loennbark & Lundstrom (2013), Finance Research Letters
DOI: 10.1016/j.frl.2012.09.001

Published evidence:
- mechanical ORB framework;
- empirical application to US crude-oil futures;
- significant full-sample ORB profitability and evidence of intraday trending;
- important caveat from the paper itself: results are not robust across all subperiods and much of the full-sample success is linked to the more recent/high-volatility portion of their sample.

Interpretation:
- supports testing ORB as a real family;
- does NOT validate our exact London FX ORB specification;
- the paper's own subperiod instability is exactly why D023 has year splits and no post-result tuning.

Decision: D023 REMAINS PRIORITY 1 BECAUSE RULES WERE FROZEN BEFORE CURRENT RESULTS AND THE FAMILY HAS DIRECT PUBLISHED EMPIRICAL SUPPORT.

## Screened family 7 — relative-value pairs trading

### Gatev, Goetzmann & Rouwenhorst (2006), Review of Financial Studies
DOI: 10.1093/rfs/hhj020

Published evidence:
- daily US equities, 1962-2002;
- matched-pairs relative-value strategy;
- simple trading rule generated positive annualized excess returns in the paper;
- authors report profits generally exceeded conservative transaction-cost estimates.

Transfer limitation:
- D022 is an M15 FX residual/z-score adaptation, not an exact replication of the equities study;
- literature justifies testing relative-value mean reversion as an independent family, not assuming D022 works.

Decision: D022 REMAINS PRIORITY 2 IF THE EXACT FROZEN SYMBOL PAIRS ARE AVAILABLE.

## Screened family 8 — intraday session momentum

### Gao, Han, Li & Zhou (2018), Journal of Financial Economics
DOI: 10.1016/j.jfineco.2018.05.009
- first half-hour market return predicts last half-hour return in the S&P 500 ETF sample and other active ETFs.

### Elaut, Frommel & Lampaert (2018), Journal of Financial Markets
DOI: 10.1016/j.finmar.2016.09.002
- defines/tests first-half-hour versus last-half-hour intraday momentum in an FX market with explicit trading hours;
- finds evidence tied to trading-hour concentration/liquidity demand in RUB/USD.

Interpretation:
- D028 is an intentionally simple falsification of an observed intraday temporal-persistence phenomenon;
- exact transfer from exchange closing hours to London-centered EUR/GBP/JPY/XAU trading is uncertain, hence no signal-strength tuning in V0.

Decision: D028 REMAINS PRIORITY 4 AS A HIGH-COUNT, CHEAP FALSIFICATION TEST.

## Result of the screen

The current four-strategy target remains sensible:
1. D023 London ORB M15;
2. D022 relative-value pair reversion M15, only if all frozen legs exist;
3. D027 NR7 contraction breakout;
4. D028 intraday session momentum.

Optional fifth: D029 classic TSMOM benchmark.

Reserve candidate: H4 bullish/bearish engulfing replication, but ONLY after exact published methodology is recovered. Do not guess missing rules.

The academic screen also produced one useful kill before coding: FX fixing reversal is not suitable for client/prop execution because the paper reports negative transaction-cost-adjusted client strategy returns.
