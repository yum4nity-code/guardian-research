# GUARDIAN — Crossed Economic Phenomena Matrix V1

Date: 2026-09-22  
Status: DESIGN COMPLETE — NO NEW EDGE TRIALS RUN  
Scope: phenomena actually testable from already-owned Guardian data/code.  
Protected rule: no 2026 access. New lineages must not use 2023-2025 for design/selection.

## 1. Inventory of usable assets

### A. Core intraday market layer — READY
Existing causal M1/M5 history and feature machinery for:
- XAUUSD
- XAGUSD
- UDXUSD
- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCHF
- USDCAD
- SPXUSD
- NSXUSD
- WTIUSD
- BCOUSD

Already implemented causal fast features include:
- returns 5/15/30/60/120/240m;
- realized volatility 30/60/240m;
- trend 60/240m;
- z-return 60/240m;
- cross-market dispersion;
- cross-market positive fraction;
- deterministic time state.

Forward targets already exist at:
5/15/30/60/120/240m.

### B. US rates / curve layer — READY FOR NEW INTERACTIONS
Available transforms already built from official Treasury nominal and real curves:
- nominal curve levels;
- real curve levels;
- breakevens where nominal/real tenors overlap;
- nominal slopes 2s10s, 5s10s, 10s30s, 5s30s where available;
- real slopes;
- d1 / d5 changes;
- long-window z-scores.

Standalone V102/V103 rate signals are CLOSED.
This does **not** ban materially new interaction/decomposition hypotheses.

### C. CFTC positioning — READY FOR NEW INTERACTIONS WITH CORRECT UNIT OF EVIDENCE
Causal weekly Futures Only data and exact mappings exist for:
XAU, XAG, EUR, GBP, JPY, AUD, CAD, CHF, SPX, NSX, WTI.

Existing transforms:
- commercial net % OI;
- noncommercial net % OI;
- level;
- d1w;
- d4w;
- z52.

Standalone CFTC lineage V104/V105 is CLOSED because effective information count collapsed to very few distinct reports.

New interaction studies must:
- treat report/week as the slow information state;
- not count carried 5m rows as independent positioning observations;
- cluster/infer by report week and use distinct price/event occurrences.

### D. Treasury auctions — READY, CONSERVATIVE AVAILABILITY
Canonical auction source:
- 9,496 rows;
- 1979-10-31 through 2022-12-29;
- auction_date;
- bid-to-cover;
- high yield/rate and other auction fields;
- security type/term buckets.

V109 standalone auction alpha is CLOSED.
For interaction studies use:
AVAILABLE_AT = auction_date + 1 calendar day.

Therefore immediate auction-reaction claims are **not** allowed. Only next-day/later conditioning is currently defensible.

### E. Existing multi-source architecture — READY
Already built:
- slow causal state matrix;
- 5m fast price-state matrix;
- slow->fast causal as-of bridge;
- feature family taxonomy;
- cross-family interaction engine;
- conditional-edge engine;
- incremental parent/interaction attribution machinery.

Important: V85 already searched broad cross-family LO/HI conjunctions.
The matrix below therefore avoids re-running the same state-pair search.

### F. External Intelligence Bus — READY FOR FORWARD EVENT STUDIES, NOT LONG-HISTORY BACKTEST
Validated raw/replay layer for BTC/ETH includes:
- spot;
- perpetual;
- open interest;
- funding;
- liquidation events;
- estimated liquidation notional;
- strict available_at replay.

Multi-venue code exists for Bybit + Binance and derives:
- basis;
- spot/perp return dislocation;
- OI changes;
- liquidation confirmation;
- cross-venue price/funding/basis/OI disagreement.

Use this only for forward/replay accumulation unless a sufficiently long immutable archive is demonstrated.

## 2. Common mathematical primitives

### Causal standardization
For any slow or fast variable:
z_t = (x_t - mean_prior_t) / sd_prior_t

All moments use information strictly prior to t.

### Rolling-beta residual
For linked assets A and B:
epsilon_A|B,t = r_A,t - beta_t * r_B,t

beta_t is estimated on a strictly prior rolling window.

This tests information in A not explained by the common driver B.

### Interaction / incremental information
Preferred statistical form:
y = alpha + beta*A + gamma*B + delta*(A*B) + error

delta tests genuine interaction.

Equivalent descriptive check:
I(A,B) = E[y|A&B] - E[y|A] - E[y|B] + E[y]

### Event definition
Repeated overlapping rows do not automatically count as independent evidence.
Use:
- non-overlapping horizon grids;
- shock cooldowns;
- distinct CFTC report weeks;
- one Treasury auction = one event;
- block/HAC inference.

## 3. Phenomena matrix

| ID | Economic phenomenon | Data crossed | Frozen object / formula | Main targets | Statistical unit | Readiness | Why materially new vs V85 |
|---|---|---|---|---|---|---|---|
| P01 | **Real-yield + USD pressure on gold** | real Treasury yield changes + UDX + XAU | residualize XAU on UDX, then test incremental real-yield shock and real-yield×USD interaction | XAU 30–240m / next-day where slow state requires | non-overlap price events, clustered by day | READY | continuous residual/decomposition, not LO/HI conjunction |
| P02 | **Inflation decomposition of precious metals** | nominal yield + real yield + breakeven + XAU/XAG | separate real-rate shock from breakeven shock; test opposite-sign decompositions | XAU/XAG 60–240m | daily slow-state changes × non-overlap target | READY | decomposition of one yield move into real/inflation components |
| P03 | **USD-residualized precious-metal shock** | XAU/XAG + UDX | epsilon_metal = r_metal - beta*r_UDX; test residual continuation/reversal | XAU/XAG 15–240m | distinct residual shocks with cooldown | READY | beta residual, not raw cross-asset states |
| P04 | **Oil -> CAD transmission beyond the dollar** | WTI/BCO + USDCAD + UDX | epsilon_CAD = r_USDCAD - beta*r_UDX; test oil shock -> future epsilon_CAD | USDCAD 15–240m | distinct oil shocks | READY | economically directed lead-lag with dollar removed |
| P05 | **Brent-WTI dislocation -> CAD / oil convergence** | BCO + WTI + USDCAD | rolling-beta WTI/Brent residual spread z; test convergence and CAD transmission | WTI/BCO/USDCAD 30–240m | spread dislocation events | READY | genuine relative-value object |
| P06 | **Nasdaq-vs-SPX duration divergence conditioned by rates** | NSX + SPX + real/nominal yields | epsilon_NSX|SPX plus rate shock; test delta interaction | NSX/SPX 30–240m | distinct equity divergence events, clustered day | READY | relative-value + macro interaction |
| P07 | **Yield-curve twist -> growth/value repricing** | 2/5/10/30Y nominal/real slopes + NSX/SPX | slope shock / curve twist × NSX-SPX residual | NSX/SPX 60–240m | daily curve-change events | READY | curve geometry, not absolute rate state |
| P08 | **Synthetic USD breadth vs UDX divergence** | EUR/GBP/JPY/CHF/CAD/AUD + UDX | predeclared equal-weight signed USD FX factor; divergence = UDX return - synthetic factor | UDX, FX, XAU/XAG 15–120m | divergence shocks | READY | cross-sectional breadth/residual |
| P09 | **Cross-market risk consensus vs disagreement** | SPX, NSX, AUDUSD, USDJPY/JPY sign, XAU, UDX | equal-weight standardized risk factor + dispersion; test consensus and disagreement separately | indices/FX/gold 30–240m | non-overlap grids | READY | latent economic breadth object rather than pair conjunction |
| P10 | **Correlation-break regime** | economically linked pairs | corr_short - corr_long and rolling-beta residual z | pair members 30–240m | first break event after cooldown | READY | dynamic relationship breakdown |
| P11 | **XAU-XAG relative-value dislocation** | XAU + XAG + UDX optional control | epsilon_XAU|XAG (and inverse); test convergence/continuation after residual extremes | XAU/XAG 30–240m | residual dislocation events | READY | true spread/stat-arb family, not old direct lead-lag |
| P12 | **CFTC crowding x own-price shock** | CFTC z52 + mapped market intraday price shock | interaction crowding_state × shock_direction; compare squeeze vs continuation | mapped XAU/XAG/FX/index/WTI 60–240m | distinct shock events, inference clustered by CFTC report week | READY | positioning as context for a separate event |
| P13 | **CFTC crowding x intermarket catalyst** | CFTC target positioning + linked leader shock | e.g. CAD crowding × oil shock; gold crowding × real-yield/USD shock | USDCAD, XAU/XAG, indices | catalyst events, clustered by report week | READY | cross-source catalyst/crowding mechanism |
| P14 | **CFTC crowding x correlation break** | positioning + rolling pair residual/correlation break | does extreme positioning predict whether divergence closes or accelerates? | XAU/XAG, oil/CAD, index pair | correlation-break events | READY | slow crowding conditions a relative-value event |
| P15 | **Treasury auction quality -> next-day cross-asset repricing** | same-bucket bid-to-cover / yield / accepted ratios + rates + USD + gold | causal same-security z/d1; AVAILABLE_AT auction+1d | rates proxy states, UDX, XAU, FX 60–240m after availability | one auction event | READY | event x cross-asset reaction; no immediate auction timestamp claim |
| P16 | **Treasury auction quality x pre-existing curve/crowding regime** | auction fields + yield curve + CFTC | interaction auction_quality × prior curve/crowding state | UDX/XAU/indices/FX after +1d availability | one auction event | READY | catalyst conditioned by independent slow regime |
| P17 | **Crypto deleveraging exhaustion** | spot/perp + OI + basis + liquidations | price shock + OI collapse + liquidation burst + marginal price impact/reclaim | BTC/ETH forward 1–60m | liquidation/deleveraging episodes | FORWARD-ONLY | true external microstructure state |
| P18 | **Cross-venue crypto confirmation/divergence** | Bybit + Binance price/basis/funding/OI/liquidations | venue spread/disagreement + same-direction confirmation | BTC/ETH forward 1–60m | cross-venue dislocation episodes | FORWARD-ONLY | venue disagreement unavailable in historical price matrix |
| P19 | **Crowded perp regime x liquidation shock** | funding + basis + OI + liquidations + spot/perp reaction | crowded_state × liquidation_direction × OI change | BTC/ETH forward 1–60m | distinct episodes | FORWARD-ONLY | economically explicit leverage-cycle interaction |

## 4. Immediate execution batches

### Batch A — highest readiness, no source repair
Run first:
- P01 real-yield + USD -> gold
- P04 oil -> CAD residual
- P06 NSX/SPX divergence x rates
- P08 synthetic USD breadth divergence
- P11 XAU/XAG relative value
- P12 CFTC crowding x own-price shock

Reason:
- every required source already exists;
- causal timing is already implemented;
- phenomena are economically distinct;
- none is merely the old V85 LO/HI Cartesian search.

### Batch B — second wave
- P02
- P03
- P05
- P07
- P09
- P10
- P13
- P14

### Batch C — event/slow-state special handling
- P15
- P16

Require one-auction-per-observation inference and no immediate-reaction claim.

### Forward-only crypto
- P17
- P18
- P19

Accumulate immutable replayable observations first. No threshold optimization from short live samples.

## 5. Explicitly NOT in the immediate matrix

### CBOE implied volatility / CFE volume-OI
Files/features exist, but V106 did not establish a sufficiently explicit causal release/availability field for promotion.
Do not use until provenance semantics are repaired/frozen.

### Financial conditions
Source exists but causal release semantics not yet good enough.

### ALFRED macro
Source support exists, but V107 architecture was closed operationally after repeated source->target bridge failure.
Do not reopen without a separate architecture rewrite.

### FOMC / Fed communication
Corpus exists, but exact historical event/publication table still needs audit.

### EIA fundamentals
Blocked until exact AVAILABLE_AT semantics are built.

### Macro surprise = Actual - Expected
Guardian currently does not possess a verified historical consensus-expectations dataset.
Do not manufacture "surprise" from actual-vs-previous.

### FX carry / international rate differential
Current verified rate layer is US Treasury-centric.
Do not call US-yield-only features a true cross-country carry differential.

## 6. Scientific rule for this program

Before code, every campaign must state:

1. economic phenomenon;
2. source variables and exact availability;
3. derived economic object;
4. statistical unit of evidence;
5. control/baseline;
6. incremental-information test;
7. discovery/replication/validation windows;
8. multiplicity budget;
9. execution relevance.

No campaign may begin with "try N random combinations and keep the best".

## 7. Recommended next action

Preregister Batch A as six separate phenomenon lineages sharing common causal infrastructure.

Do not open 2023-2025 for design.
Do not open 2026.
Do not modify the OOS-confirmed AUDUSD H21 lineage.
