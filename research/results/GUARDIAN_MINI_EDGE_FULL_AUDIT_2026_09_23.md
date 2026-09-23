# GUARDIAN — Full Mini-Edge Audit After Local Extraction

Date: 2026-09-23
Status: METHODOLOGY AUDIT COMPLETE / RESEARCH STILL PAUSED
Source extraction: GUARDIAN-MINI-EDGE-EXTRACTOR-1.2
Local receipt:
- files inspected: 2,149
- metric observations: 8,654,240
- automatic positive-but-rejected flags: 924
- extraction errors: 0
- no research rerun
- no market-data modification

## Interpretation rule

The 924 automatic flags are NOT 924 edges. They are row/document-level leads and include repeated rows from the same family, diagnostics, carried-row slow-data artifacts, variants invalidated by time-semantic repairs, and genuine economic failures with some positive submetric.

This audit keeps every historical formal pass/fail verdict intact. It adds a separate retrospective classification:
- CONFIRMED_EDGE_OR_PHENOMENON
- MINI_EDGE_CANDIDATE
- WEAK_COVARIATE_CLUE
- GENUINE_REJECT / DO_NOT_REVIVE

The point is to stop conflating "not large enough to trade alone" with "no predictive information".

---

## A. Existing confirmed edges / phenomena

### V112 — AUDUSD H21 120m SHORT
Locked OOS 2023-2025:
- n = 556
- mean = +1.455235 bp
- matched-control effect = +1.475273 bp
- net after 1 bp = +0.455235 bp
- trim best 2% = +0.978983 bp
- leave-one-year-out minimum = +1.062776 bp
- month bootstrap q2.5 = +0.811083 bp

Classification: CONFIRMED_EDGE_OR_PHENOMENON.
This already proves Guardian has found a fresh locked-OOS effect. It is not yet an execution-complete trading system; timezone/server semantics remain a deployment audit item.

### D032-C1 — Bullish Doji Star H1 entry edge
Independent pre-2024 confirmation:
- n = 79 clean events
- mean executable +24h = +133.52 bps/event
- mean = +0.588R/event
- month-block bootstrap 95% lower bound about +10.1 bps
- 3/3 core symbols positive in mean
- aggregate Doji-control differential +101.38 bps/event

Classification: CONFIRMED_EDGE_OR_PHENOMENON.
The entry effect is formally confirmed. The tested -1R/+3R management was not confirmed, so execution/risk management is the unresolved layer.

---

## B. Strong mini-edge candidates that were under-classified by the old large-edge doctrine

### EA01-XR-RSI-LONG-V1 — XAU RSI long — OOS 2023-2025
Historical verdict: KILL.

But the actual frozen OOS result is:
- raw signals = 944
- non-overlap n = 654
- cost 0.10: mean +0.0622R/trade, PF 1.087
- stress cost 0.20: mean +0.0158R/trade, PF 1.021
- temporal gate passed: 2 positive years required, 2 achieved
- 2023: -0.0035R
- 2024: +0.0431R
- 2025: +0.1772R

The primary gate failed because PF was 1.087 versus a frozen PF >= 1.10 hurdle. Mean edge remained positive and the stress case also remained positive.

Classification: MINI_EDGE_CANDIDATE — HIGH INTEREST.
This is the clearest example in the archive of a fresh OOS-positive effect killed by a narrow standalone-PF threshold.

### R5E-023 — XAU M5, news-clean, sma5 low-tail, LONG, 48 bars
Pre-OOS economic robustness only; protected 2026 was not opened by this experiment.

Historical verdict: FAIL.
Fail reasons ONLY:
- TRADE_COUNT_2024_LT_100
- TRADE_COUNT_2025_LT_100

2024:
- 62 trades
- E1 expectancy +2.7489 engine units / +10.732 bps
- PF 4.296
- stress expectancy +1.4993 / +5.589 bps
- stress PF 2.138

2025:
- 83 trades
- E1 expectancy +10.7176 / +30.808 bps
- PF 7.370
- stress expectancy +8.9812 / +25.659 bps
- stress PF 5.066

Both 2025 half-years remain positive under E1 and stress. Excluding the single best positive trade also leaves both years positive.

Classification: MINI_EDGE_CANDIDATE — HIGH INTEREST, BUT NOT FRESH-OOS CONFIRMED.
The old rejection was a sample-count rule, not an economic failure.

### R5E-042 — XAU M5 ret24 upper-tail, SHORT, 48 bars
Historical verdict: FAIL.
Fail reasons ONLY:
- 89 trades in 2024 instead of 100
- 89 trades in 2025 instead of 100

2024:
- E1 +8.484 bps, PF 2.342
- stress +3.347 bps, PF 1.411

2025:
- E1 +9.827 bps, PF 1.759
- stress +4.691 bps, PF 1.271

Caveat: 2025 H2 stress becomes negative (-1.602 bps; PF 0.869), and H2 ex-best E1 net is negative.

Classification: MINI_EDGE_CANDIDATE — MEDIUM INTEREST.
The annual rejection was count-only, but the within-2025 stress instability is real.

### D035-E1 — causal BTC+ETH dual-source -> XLM response
- primary n about 870
- executable +15m mean +6.705 bps
- raw day-cluster bootstrap 95% lower +1.996 bps
- event-control differential +13.490 bps
- differential bootstrap lower +8.793 bps
- executable +30m +3.697 bps
- 2024 +4.104 bps
- 2025 +9.935 bps
- frozen gate: 6/8 pass

It was stopped mainly because the project demanded >=15 bps executable mean and median >0.

Classification: MINI_EDGE_CANDIDATE — HIGH INTEREST AS SIGNAL/COVARIATE.
A measurable causal conditional response remained after fixing the dual-source look-ahead issue. It was too small for the old standalone hurdle, not absent.

### D017 — BTC SELL Momentum
Long-history branch:
- pooled n = 761
- EV2 +0.080R
- EV2.5 +0.131R
- EV3 +0.125R
- 2024 EV2.5 +0.150R / EV3 +0.170R
- 2025 EV2.5 +0.114R / EV3 +0.085R
- descriptive native management about +0.109R
- positive in both 2024 and 2025

Classification: MINI_EDGE_CANDIDATE — MEDIUM/HIGH.
It was explicitly rejected as a production engine because it sat below the user's old ~+0.15R large-edge standard and lacked a large cost cushion.

### D025 — ETH RETEST continuation
- 2024 EV2 +0.084R
- 2025 EV2 +0.109R
- pooled 2024-2026 n = 704
- pooled EV2 +0.133R before costs
- Wilson interval for +2R hit probability remained above theoretical pre-cost break-even

Classification: MINI_EDGE_CANDIDATE — MEDIUM/HIGH.
Needs proper cost/execution modelling before economic promotion.

### D025 — EURUSD SHORT -> +2R
- 2024 EV2 about +0.146R
- 2025 EV2 about +0.122R
- pooled 2024-2025 about +0.136R pre-cost
- monthly cluster interval still crosses zero

Classification: MINI_EDGE_CANDIDATE — MEDIUM.
Positive point estimates repeat across both full years; uncertainty and costs remain unresolved.

### D025 — GBP SHORT +1R
Original 1.01:
- pooled about +0.121R
- 2024 +0.070R
- 2025 +0.183R
- small 2026 sample +0.118R
But later 1.02 weakens materially.

Classification: MINI_EDGE_CANDIDATE — LOW/MEDIUM because protocol/population instability is real.

---

## C. Historical candidates where robustness gates were probably too severe, but current evidence is mixed

### NIGHT ATLAS F14_PDAY_FAILED
2017-2022:
- n = 1,087
- cost 0.10 mean +0.2051R, PF 1.167
- cost 0.20 mean +0.1254R, PF 1.099
- 5/6 positive years
- all leave-one-year-out means positive
- without top 1% winners at cost 0.10 still +0.0559R
- failed only because daily bootstrap CI lower was slightly below zero (-0.022R)

This looked like a classic severity casualty.

However the later F14-V2 locked OOS 2023-2025 is negative:
- n=134
- cost 0.10 mean -0.207R, PF 0.865
- cost 0.20 mean -0.250R

Classification: GENUINE LATER CONTRADICTION / DO NOT REVIVE AS CURRENT EDGE.
Useful as evidence that the old gate was severe, but the later OOS prevents treating the lineage as alive.

### NIGHT ATLAS F16_DAYOPEN_EXTREME
2017-2022:
- n=1,392
- cost0.10 mean +0.2214R, PF1.159
- cost0.20 mean +0.0736R, PF1.050
- 5/6 positive years
- all LOO means positive
- failed only bootstrap lower >0

But mean without top 1% winners turns negative, and 2022 is negative.

Classification: WEAK/MEDIUM MINI-EDGE CLUE, tail-sensitive and not fresh-OOS confirmed.

### NIGHT ATLAS F13_PDAY_BREAK
2017-2022:
- n=2,338
- cost0.10 mean +0.2469R
- cost0.20 mean +0.1430R
- 5/6 positive years
- all LOO positive
- failed only bootstrap lower >0

But one extreme winner is ~+427R; removing top 1% winners flips the mean negative.

Classification: DO NOT CALL ROBUST MINI-EDGE; tail dependence is a real problem.

### ATLAS IV A4_02_REALIZED_SKEW_REVERSAL
2017-2022:
- development 2017-2020 cost0.10 +0.0585R
- internal holdout 2021-2022 cost0.10 +0.1170R, PF1.189
- holdout cost0.20 +0.0275R
- full n=6,123
- full cost0.10 +0.0740R, PF1.109
- signal-v-control daily delta +0.3237, CI entirely positive, BH q ~0.000375
- all LOO signal means positive
- 5/6 positive years

Strict freeze failed because:
- full cost0.20 turns negative
- daily signal bootstrap lower crosses zero
- removing top1% winners turns mean negative

Classification: MINI_EDGE/COVARIATE CANDIDATE — MEDIUM.
The control-relative information looks materially stronger than the standalone PnL robustness. Good ensemble/covariate research material, not standalone production evidence.

---

## D. Calendar candidates that were blocked by robustness diagnostics before OOS

V111 had five pre-OOS rejects despite positive means. Four failed only one additional forensic gate:
- C1 XAGUSD H11 60m: n1289, +3.126 bp, net1bp +2.126, LOO min +2.707, bootstrap q2.5 +1.164; trim5 negative.
- C5 USDCHF H22 240m: n1047, +1.693 bp, net1bp +0.693, trim5 +0.463, LOO min +1.080, bootstrap +0.956; one timing-shift gate failed.
- C7 AUDUSD H21 240m: n1033, +1.304 bp, net1bp +0.304, LOO min +1.033, bootstrap +0.542; trim5 negative.
- C8 EURUSD H11 120m: n1295, +1.628 bp, net1bp +0.628, LOO min +1.180, bootstrap +0.759; trim5 negative.

Classification: UNCONSUMED MINI-EDGE CANDIDATES UNDER A NEW DOCTRINE.
Do not retroactively call them OOS passes. They simply should not be labelled "no edge" solely because one robustness diagnostic failed.

The V112 AUDUSD H21 120m candidate that DID reach locked OOS passed, which supports the general point that this calendar family contains real signal.

---

## E. Weak positive clues that should be retained only as covariates

### M04 AUDUSD/UDX L15
Locked OOS 2023-2025:
- n=1,467
- mean endpoint +0.0697
- p=0.1034
- 2023 and 2024 positive, 2025 negative
- all leave-one-year-out means positive
- trims turn negative

Classification: WEAK_COVARIATE_CLUE.
Formal locked-OOS verdict remains FAIL. It is not zero information, but it is too weak/tail-sensitive to rescue as standalone M04.

### M04 GBPUSD/UDX L15
2018-2022 validation:
- positive mean +0.06355
- p=0.053625

Classification: WEAK_COVARIATE_CLUE.
The p=0.05 cutoff killed it narrowly; no fresh locked OOS was consumed for this exact candidate.

### D030 ETH H4 Engulfing confirmation
Pre-2024:
- n321
- mean executable +0.0396R
- cleaner no-gap subset only about +0.0127R
- direction/time robustness weak

Classification: WEAK_COVARIATE_CLUE, not a strong revival candidate.

### D034 XAU abnormal return
- n83
- mean +1.89 bps
- median positive
- temporal and directional stability weak

Classification: WEAK_COVARIATE_CLUE.

---

## F. Large groups that should NOT be revived just because the extractor found positive fields

### V102/V103 rates
Slow-event carried-row semantics inflated repeated observations. The event/report-first forensic breaks many candidates. Statistical unit must be true release/event. Positive carried-row metrics are not valid mini-edges.

Classification: GENUINE_REJECT / DO_NOT_REVIVE without a genuinely new event-level lineage.

### V104/V105 CFTC
Same problem: report-first / episode-first forensic collapses the apparent repeated-row effects for the candidates.

Classification: GENUINE_REJECT / DO_NOT_REVIVE.

### V93 old cross-asset BCO candidate
Old locked OOS looked positive (BCO 15m LONG), but V97D corrected time semantics and rescored the panel; the candidate became negative.

Classification: INVALIDATED_BY_TIME_REPAIR / DO NOT_REVIVE.

### R13 failed-breakout family
A few tiny samples remain gross/stress positive, but FDR q values are around 0.9 and sample sizes are small. This is discovery noise, not evidence that severity killed a good edge.

Classification: DO NOT PRIORITIZE.

### 2026 phase IF/IJ XAU features
Several full-sample effects are positive, but Jan-Apr versus May-Aug signs flip sharply.

Classification: REGIME_UNSTABLE / GENUINE REJECT as stable standalone edge.

### E2 final OOS supplement
Small positive point estimate under base cost disappears under stress and controls / concentration are weak.

Classification: GENUINE WEAK FAIL.

---

## Main audit conclusion

The user's concern is substantiated.

Guardian did NOT fail because every discovered phenomenon was fake. The archive contains:
1. at least two already formally confirmed predictive phenomena;
2. multiple repeatable positive mini-edges that were never promoted because the project was tuned to find large standalone edges;
3. several fresh/OOS or holdout-positive candidates killed by narrow PF, magnitude, trade-count, or repeated-significance hurdles;
4. many genuine failures that correctly died after time repair, event-unit repair, fresh OOS, cost stress, or regime reversal.

The central methodological error was therefore TAXONOMIC:
"not standalone production-ready" was repeatedly stored/interpreted as "no edge".

## New doctrine recommended before research resumes

### Stage 1 — Existence
After multiple-testing control in discovery, a fresh sample should classify the signal as:
- NEGATIVE
- POSITIVE_UNCERTAIN
- POSITIVE_CONFIRMED

Do not require +0.15R or +15 bps to say an effect exists.

### Stage 2 — Economic size
Separately classify:
- COVARIATE_ONLY
- MINI_EDGE
- STANDALONE_EDGE

Apply realistic cost/slippage here.

### Stage 3 — Ensemble value
Test whether mini-edges add incremental predictive information versus existing signals. A +0.03R to +0.10R signal can be useful if independent/diversifying.

### Stage 4 — Production
Only here apply hard PF, drawdown, concentration, liquidity, execution and prop-firm constraints.

Repeated p<0.05 gates should not be the universal death criterion at every stage.

## Immediate shortlist for methodological re-evaluation

Highest-interest existing evidence, without changing any historical verdict:
- EA01 XAU RSI LONG OOS 2023-2025
- R5E-023 XAU M5
- D035-E1 causal dual-source response
- D017 BTC SELL Momentum
- D025 ETH RETEST
- D025 EURUSD SHORT +2R
- ATLAS-IV A4_02 as a covariate/ensemble signal
- V111 C1/C5/C7/C8 as pre-OOS calendar candidates under a revised doctrine
- M04 AUDUSD only as a weak covariate clue

Already confirmed and should not be forgotten:
- V112 AUDUSD H21 120m SHORT
- D032-C1 Bullish Doji Star H1 entry edge

## Research status

Remain PAUSED until the new validation taxonomy/gates are written and frozen.
Do not rerun or rescue any historical candidate under ad-hoc thresholds.
No protected-2026 opening is authorized by this audit.


## Addendum — R5E-023 protected 2026 OOS located after audit

A preregistered protected Jan-Aug 2026 OOS already existed on the backtest-results branch and materially changes the retrospective interpretation.

- n=89
- full E1 PF 1.0255, net +29.62
- full STRESS PF 0.8598, net -178.16
- Jan-Apr E1 expectancy +6.6509
- May-Aug E1 expectancy -5.8449
- full E1 ex-best positive net -74.47
- bootstrap p05 -5.6973
- historical protected-OOS verdict FAIL

Updated classification: GENUINE LATER OOS CONTRADICTION / DO NOT REVIVE.
