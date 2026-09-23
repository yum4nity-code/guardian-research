# GUARDIAN — Interesting / Preserved Edges Shortlist

Date: 2026-09-23
Purpose: persistent shortlist of results worth remembering across sessions.

## ACTIVE / KEEP

### 1) V111 C8 — EURUSD H11 SHORT 120m
Status: **KEEP — first FTMO execution survivor**

Frozen rule:
- EURUSD
- SHORT
- H11 -> H13 in source convention
- 120-minute hold
- no signal filter, no TP/SL optimization

Evidence:
- fresh source OOS 2023-2025: n=717, mean +1.507838 bp/trade
- all three OOS years positive
- month-block q10 +0.836784 bp; q2.5 +0.511265 bp
- FTMO alignment +2h, 717/717 coverage
- FTMO BID/ASK after observed spread: +1.005565 bp/trade
- after current Forex commission assumption: about +0.550 bp/trade
- production caveat: small residual friction budget (~0.55 bp); 2024 slightly negative after commission

Interpretation:
- statistically confirmed source edge
- survives FTMO observed spread
- survives current commission on average
- mini-edge / not yet production-ready
- preserve exact timing; do not retune

### 2) D035-E1 / D035-F1 — causal BTC+ETH dual shock -> XLMUSD SHORT
Status: **KEEP — FTMO FRESH RESULT POSITIVE_UNCERTAIN / MINI-EDGE**

Frozen rule:
- causal BTCUSDT + ETHUSDT downside/OI shock within <=5m
- signal = later / second qualifying source shock
- target XLMUSD only
- SHORT
- primary exit +15m
- +30m diagnostic only

Historical evidence:
- causal dual events 973; XLM rows 870
- mean executable +15m ~+6.705 bp
- control ~-6.786 bp
- differential ~+13.49 bp
- raw bootstrap 95% roughly [+1.996,+11.549] bp
- differential bootstrap roughly [+8.793,+18.302] bp
- 2024 +4.104 bp; 2025 +9.935 bp

Fresh FTMO 2026-H1 result:
- 254 source events; 245 executable +15m target events
- gross executable +15m +6.639 bp
- net after FTMO commission +0.141 bp
- matched control -11.880 bp
- event-control differential +12.416 bp
- bootstrap q10 -5.856 bp; P(mean<=0) 0.483
- trim best 1% -> -2.640 bp
- +30m diagnostic -8.769 bp

Interpretation:
- conditional/relative phenomenon remains interesting
- current exact FTMO implementation is economically too thin standalone
- retain for ensemble/incremental-value research
- no retuning; Jul-Dec 2026 and other targets remain blocked

### 3) EA01-XR-RSI-LONG-V1 — XAU RSI long
Status: **PRESERVE FOR ENSEMBLE / MINI-EDGE RESEARCH**

Existing OOS 2023-2025:
- non-overlap n=654
- cost 0.10R mean +0.06216R, PF 1.0868
- stress cost 0.20R mean +0.01576R, PF 1.0213
- bootstrap q10 negative
- trim best 1% turns negative

Interpretation:
- positive-uncertain
- stress-positive
- not standalone production-ready
- retain for future ensemble/incremental-value work, not as a single deployed strategy

## INTERESTING HISTORICAL PHENOMENA — CLOSED FOR FTMO

### D032-C1 Bullish Doji Star H1
- historical pre-2024 confirmation was strong
- exact canonical FTMO transport later failed: pooled n=226, about -62.21 bp/event
- preserve as feed-specific research phenomenon
- do not retune for FTMO

### V111 C1 XAGUSD H11 SHORT 60m
- fresh source OOS remained positive (~+1.19 bp)
- gross phenomenon transferred to FTMO
- FTMO spread killed it (~-4.97 bp executable)
- preserve as statistical phenomenon only

### V69 USDCHF Friday LONG
- historical and locked OOS phenomenon confirmed
- exact FTMO execution rejected after spread
- preserve research finding, do not deploy

### V112 AUDUSD H21 SHORT 120m
- gross phenomenon confirmed
- FTMO boundary spread killed the frozen implementation
- preserve research finding, do not deploy

## CLOSED / DO NOT RESCUE

- V111 USDCHF H22 LONG 240m — fresh OOS negative
- V111 AUDUSD H21 SHORT 240m — fresh endpoint negative
- D025 ETH RETEST +2R — fresh FTMO 2023 negative
- D017 BTC SELL Momentum +2.5R — fresh FTMO 2023 negative
- R5E-023 — protected 2026 contradiction / regime reversal

## Current deployment-oriented priority

1. Finish D035-F1 FTMO 2026-H1.
2. Keep EURUSD H11 SHORT 120m frozen for forward shadow / production-readiness checks.
3. Keep EA01 XAU only as ensemble candidate.
4. Do not rescue execution-rejected or fresh-OOS-negative branches.
