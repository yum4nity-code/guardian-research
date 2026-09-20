# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-20**

This top section supersedes older state descriptions below. Historical material remains evidence, not current instructions.

## Read first
1. `GUARDIAN_MASTER_MANDATE.md`
2. `EDGE_FAMILY_MAP.md`
3. `docs/RESEARCH_PROTOCOL.md`
4. this handoff
5. `START_HERE_NEXT_AI.md`

## Current mission
Find a reproducible, causal, economically plausible market edge from free data. Guardian infrastructure/risk management does not create alpha.

Temporal discipline for the current Edge Factory:
- discovery: 2010–2013
- replication: 2014–2017
- validation: 2018–2022
- locked OOS: 2023–2025
- protected: 2026

Never select/tune with validation or OOS. Every survivor set is frozen before the next period. No automatic live deployment.

## Current active lineage
**V32/V33 — volatility-regime × price-shock continuation/reversal.**

V32 discovery completed on 2010–2013 only:
- 8 markets: XAUUSD, XAGUSD, SPXUSD, NSXUSD, WTIUSD, EURUSD, GBPUSD, USDJPY
- M15
- fixed realized-vol regimes: compressed / normal / expanded
- fixed shock: absolute M15 return >= past-only rolling 20-day 95th percentile, threshold shifted one bar
- horizons 30/60/120/240m
- continuation and reversal
- 192 cells, 56 screen survivors, **16 frozen for replication**
- 2014+ was not accessed by V32.

V33 runner is committed and is the **next active action**:
`automation/Run-GuardianEdgeFactoryV33.ps1`
It replicates all 16 frozen V32 candidates on 2014–2017 with no retuning and requires all four replication years to be present. It stops before 2018.

After V33:
- if no survivors: close family 3 and move according to `EDGE_FAMILY_MAP.md`;
- if survivors: pre-validation robustness on 2014–2017; do **not** open 2018–2022 yet.

## Edge-family map
`EDGE_FAMILY_MAP.md` is now the canonical map of the research possibility space. It tracks 28 large families as UNTOUCHED / EXPLORING / EXHAUSTED / PROMISING and defines the research queue.

Current high-level state:
- simple price momentum/continuation: exhausted under tested formulations;
- simple price mean reversion: exhausted under tested formulations;
- volatility regime × shock: **EXPLORING (V32/V33)**;
- broad price-only cross-asset lead/lag: closed/exhausted;
- most external-information families remain untouched: implied volatility, vol term structure, CFTC positioning, nominal/real rates, breakevens, macro/FOMC, Treasury auctions, etc.

## Recent closed lineages — do not rescue
- GBP60 V3–V10: invalidated by confirmed M5 timestamp lookahead; causal V11 negative.
- XAG zret_12b H240 P97.5: persistent phenomenon but V19 strict pre-OOS gate failed because removing best 1% trades made mean negative. Locked OOS untouched.
- V20–V28 XAU/XAG cross-market: closed before locked OOS. V25 had one validation survivor (XAG<-XAU divret_6b H240 P99), but V26 temporal forensic failed; V27 showed fresh quotes did not remove baseline; V28 attribution showed divergence +9.745 bp versus same-event XAG mean reversion +9.462 bp — insufficient incremental XAU information.
- V29–V31 clean XAG-only mean reversion: 12 frozen, 7 replicated, **0/7 passed pre-validation robustness**. 2018–2022 remained untouched for this lineage.

## Important data/integrity facts
- Causal M5 core uses right-edge availability semantics; never reintroduce left-labeled cache behavior.
- Cross-market timestamp-grid overlap is not proof of vendor timezone truth.
- Costs tested as generic sensitivity are not empirical broker execution costs.
- Daily sign-flip null is a dependence-preserving diagnostic, not a complete DGP null.
- EIA data must not enter alpha research until causal `AVAILABLE_AT` is built.
- CFTC must use publication lag.
- Revised macro series require vintage-correct ALFRED where relevant.
- 2023–2025 is scarce locked OOS; 2026 is protected.

## Data lake available
Local root: `D:\MT5_Backtests\DataLake`.
Useful sources already acquired include HistData M1 multi-market, Treasury nominal/real yields, CFTC history, Cboe VIX/VVIX/VIX9D/OVX/GVZ, FRED plus ALFRED vintage-correct series, Fed/FOMC corpus, Treasury auctions, EIA WPSR (availability timing unresolved), and CFE volume/OI.

## Research sequence after current family
Follow `EDGE_FAMILY_MAP.md`, not ad-hoc “next” ideas:
1. finish regime/shock lineage;
2. implied-volatility state / term structure;
3. nominal rates / real yields / breakevens;
4. CFTC positioning;
5. macro/FOMC events;
6. Treasury auctions;
7. energy fundamentals only after EIA causal timing is solved;
8. interaction families only after constituent families have standalone evidence.

## Operating rules
- Every job longer than a few minutes must print progress, x/y, %, elapsed, ETA and useful provisional state.
- Inspect current code/provenance before modifying runners.
- Preserve negative results and receipts; clean non-destructively.
- Do not choose a “best” correlated variant using validation performance.
- Before locked OOS: independent validation plus pre-OOS forensic plus explicit human review.
- Never deploy live without explicit approval.

## Repository hygiene
The repository contains substantial historical D0xx/Rxx material. It is retained for provenance. **Do not treat old queue/handoff files as current state.** Current navigation is:
`README.md -> CURRENT_PROJECT_HANDOFF.md -> EDGE_FAMILY_MAP.md -> START_HERE_NEXT_AI.md`.

Older content formerly at the top of this file is intentionally superseded by this canonical 2026-09-20 handoff.
