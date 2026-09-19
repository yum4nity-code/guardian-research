# GUARDIAN EDGE FACTORY — SCIENTIFIC SPECIFICATION V1

Status: FROZEN RESEARCH DIRECTION
Date: 2026-09-19
Scope: discovery research only. No live deployment authorization.

## 1. Mission
Find reproducible, economically exploitable predictive information in the free data available to Guardian, without privileging a market, indicator, timeframe, direction, or strategy family.

Valid outcomes:
A. one robust standalone edge;
B. a composite edge built from independently useful micro-edges;
C. a diversified portfolio of strategies across markets/horizons/regimes;
D. no robust edge found.

D is scientifically valid. The system must never manufacture a winner.

## 2. Hard constraints
- Free data only. Paid datasets are excluded.
- No target market is privileged.
- 2023-2025 is LOCKED OOS and must not participate in feature selection, threshold selection, model selection, ranking, pruning, regime design, or strategy design.
- 2026 remains PROTECTED and unopened.
- Any access to locked/protected data must fail closed and be logged.
- Stop for human review before first access to 2023-2025 for a promoted candidate.
- Research does not authorize live/real-account deployment.
- Every tested hypothesis/configuration must be counted in the trial ledger.
- Infrastructure failure is not scientific rejection.
- Existing closed families are not to be blindly rerun.

## 3. Research universe
Core M1 targets, subject to verified common coverage:
XAUUSD, XAGUSD, UDXUSD, EURUSD, GBPUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, SPXUSD, NSXUSD, WTIUSD, BCOUSD.
Deduplicate symbols during implementation. XAUCHF and XAUEUR may be auxiliary/short-window inputs but must not truncate the whole universe.

Information families:
1. own-market price/path;
2. cross-market/intermarket;
3. volatility and volatility-of-volatility;
4. CFE volume/open interest;
5. CFTC positioning;
6. nominal/real rates and yield-curve state;
7. inflation expectations and financial conditions;
8. vintage-correct macro state (ALFRED);
9. Fed/FOMC information with true availability semantics;
10. Treasury auctions with true availability semantics;
11. EIA oil fundamentals with true availability semantics;
12. deterministic technical transforms generated locally.

No feature may use information before its real historical availability time.

## 4. Temporal protocol
Primary common-window protocol:
- DISCOVERY: 2010-01-01 through 2013-12-31
- REPLICATION: 2014-01-01 through 2017-12-31
- VALIDATION: 2018-01-01 through 2022-12-31
- LOCKED OOS: 2023-01-01 through 2025-12-31
- PROTECTED: 2026+

Earlier data may be used only as explicitly labelled historical stress evidence when a family supports it. It cannot silently alter selection rules after results are seen.

## 5. Targets
For every eligible market, test forward outcomes at multiple horizons where data semantics permit:
+5m, +15m, +30m, +60m, +120m, +240m, session-close and next-session/day where appropriate.

Do not force symmetric LONG/SHORT behavior. Directional asymmetry is allowed and measured.

Initial target objects should include:
- forward log return;
- sign of forward return;
- volatility-scaled forward return;
- excursion/path statistics (MFE/MAE-like future path measures) for later strategy design.

## 6. Feature Factory
Generate causal features in families rather than ad-hoc strategy recipes.

### A. Own-market state
returns, lagged returns, rolling location, range, realized volatility, volatility change, trend strength, reversal state, gap, compression/expansion, distance from rolling extrema, path efficiency, skew proxies, jump/shock measures.

### B. Time/session
minute/hour, day-of-week, month boundaries, Asian/London/New York transitions, overlap state, time since session open, time to session close. DST must be explicit and audited.

### C. Cross-market
lagged returns, relative strength, spreads/ratios where economically coherent, rolling beta/correlation, correlation break, residuals, lead-lag, confirmation/divergence, cross-sectional shock rank, volatility transmission.

### D. Volatility complex
VIX, VVIX, VIX9D, GVZ, OVX and available CFE volume/OI states: level, change, z-score, percentile, term/regime proxies where genuinely supported by the data.

### E. Rates/macro/positioning/fundamentals
Use only lagged/as-of values with historically correct availability. Construct changes, surprises only where consensus/previous-release semantics are actually available, curve slopes, real-vs-nominal states, positioning percentiles, changes in positioning, oil inventory/supply states, financial-condition regimes.

### F. Interactions/regimes
Do not enumerate all Cartesian products blindly. Promote stable first-order features, then test bounded interactions among survivors and predeclared economic interactions. Include agnostic interactions but control their search budget.

## 7. Discovery engine
Stage 0 — data audit:
schema, timezone, coverage, duplicate timestamps, missingness, stale values, causal availability, boundary leakage.

Stage 1 — univariate phenomenon scan:
For every target/feature/horizon/direction, compute sample count, conditional expectancy, effect size, robust uncertainty, rank/IC where applicable, year-by-year stability, sign consistency and sensitivity to nearby windows/thresholds.

Stage 2 — cheap rejection:
Reject effects driven by tiny N, one year, one extreme episode, unstable sign, obvious timestamp leakage, duplicate/correlated feature aliases, or economically impossible availability.

Stage 3 — replication:
Freeze phenomenon definition before 2014-2017. No threshold retuning on replication.

Stage 4 — validation:
Only replicated families reach 2018-2022. Changes after viewing validation create a new experiment lineage and cannot inherit the old validation claim.

## 8. Micro-edge library
A micro-edge may be retained even if not independently tradeable when:
- effect direction replicates;
- effect is not concentrated in one episode;
- information is causally available;
- effect survives reasonable perturbations;
- it contributes information not fully explained by an already retained feature.

Store dependency clusters so ten aliases of the same phenomenon do not count as ten independent edges.

## 9. Edge Composer
Only compose promoted micro-edges.

Candidate forms:
- additive standardized score;
- bounded voting;
- conditional gating;
- regime-specific specialist;
- sparse linear/logistic model;
- simple tree/rule model with strict complexity limits;
- portfolio of independent strategy sleeves.

Composition must be trained on development data only. Search budgets and all configurations count toward multiplicity.

The goal is not maximum in-sample Sharpe. Prefer broad basins, stability, low complexity, independent information and low sensitivity.

## 10. Negative controls / anti-bullshit layer
Run the same discovery machinery on controls such as:
- permuted target blocks preserving local distributional properties;
- circularly shifted explanatory series;
- randomized event labels;
- synthetic/noise features matched in missingness/frequency;
- deliberately impossible future-shift tests that MUST be detected by leakage guards.

Compare real discovery yield against null discovery yield. A factory that routinely finds similarly strong edges in controls fails validation.

## 11. Multiple-testing and overfitting control
Maintain a global immutable trial ledger including rejected trials.

Use appropriate controls by experiment family:
- false-discovery-rate control for large related hypothesis families;
- bootstrap/permutation null distributions;
- Deflated Sharpe Ratio only when a strategy-return object and effective number of trials make its assumptions meaningful;
- CSCV/PBO for strategy-selection families where sufficient comparable configurations exist;
- purged/embargoed time-aware validation where labels overlap.

Do not report raw p-values or raw Sharpe as proof of edge.

## 12. Robustness gates
Promoted candidates must be stress-tested for:
- year stability;
- subperiod stability;
- neighboring thresholds/windows;
- execution delay;
- spread/commission/slippage assumptions;
- missing-data perturbation;
- market/session subsets;
- regime dependence;
- removal of best trades/days;
- bootstrap uncertainty;
- correlated-feature substitution;
- data-source quirks where relevant.

A sharp optimum is evidence against robustness.

## 13. Strategy conversion
Only after a phenomenon/composite survives scientific validation:
1. define executable entry semantics;
2. define baseline time/event exit before complex management;
3. apply realistic costs;
4. test simple stops/targets only as execution/risk design, not alpha creation;
5. compare manager variants on exactly matched entry populations;
6. add FTMO/prop-firm compliance only after economic edge exists.

Risk sizing never creates alpha.

## 14. Promotion gate before LOCKED OOS
Create a candidate dossier containing:
- exact hypothesis lineage and trial counts;
- data provenance/hashes;
- feature availability semantics;
- discovery/replication/validation results;
- null-control comparison;
- multiplicity adjustment;
- robustness matrix;
- execution/cost stress;
- parameter-basin evidence;
- dependence on regimes/markets;
- known failure modes;
- frozen code/config SHA.

Then STOP. Human approval is required before opening 2023-2025.

2026 remains protected unless separately and explicitly authorized later.

## 15. Computational strategy
Use vectorized/columnar research for broad scans. Do not use MT5 for first-pass hypothesis enumeration.

Order:
DATA AUDIT
-> FEATURE CACHE
-> TARGET CACHE
-> UNIVARIATE SCAN
-> CHEAP REJECTION
-> REPLICATION
-> MICRO-EDGE LIBRARY
-> INTERACTION/COMPOSITION
-> VALIDATION
-> NULL/ROBUSTNESS
-> EXECUTION MODEL
-> CANDIDATE DOSSIER
-> HUMAN GATE
-> LOCKED OOS

Cache deterministic features by hash. Resume interrupted jobs. Never recompute unchanged partitions unnecessarily.

## 16. Mandatory receipts
Every run writes:
- run_id;
- code/config/data hashes;
- exact temporal boundaries;
- targets/features attempted;
- number of hypotheses/configurations tested;
- rejected/promoted counts by gate;
- errors separated into INFRASTRUCTURE vs SCIENTIFIC;
- wall-clock/runtime;
- output paths;
- locked/protected-access assertion.

## 17. Existing evidence
Do not blindly rerun known dead research merely to enlarge the search count. Existing closed families remain evidence:
- simple XAU M5 Mega Atlas I: closed;
- London Gold Fix event family: closed;
- tested volatility-expansion family: closed;
- other historically rejected Guardian families retain their recorded status.

New information, materially new semantics, or a preregistered independent test is required to reopen a closed family.

## 18. Definition of success
Success is not a pretty backtest. Success is one of:
- a standalone edge that survives the full pre-OOS protocol;
- a composite whose components have reproducible incremental information;
- a diversified multi-strategy set whose combined behavior survives the same controls;
- a rigorous conclusion that the searched space contains no usable edge.

The factory must optimize the probability of discovering truth, not the probability of displaying profit.
