# Guardian Research — CURRENT PROJECT HANDOFF

## Canonical current state — 2026-09-13

Read `START_HERE_NEXT_AI.md`, this file, the durable mandates, the current queue append, and latest `backtest-results` evidence before acting.

## Closed evidence

- R4 close-to-close XAU family: CLOSED after causal-capture forensic work.
- R5 causal-next-open XAU family: CLOSED for tradable-alpha promotion after pre-OOS economic robustness scientific FAIL, 0/96 under inherited costs.
- R8 BTC/ETH relative-value mean reversion: CLOSED, scientific FAIL, 0/54 discovery survivors.
- R9 BTC/ETH UTC calendar/session seasonality: CLOSED, scientific FAIL, 0/672 discovery survivors.
- R10 BTC/ETH multi-day time-series trend: CLOSED, scientific FAIL, 0/72 discovery survivors.
- R11 BTC/ETH cross-market lead-lag shock spillover: CLOSED, scientific FAIL, 0/72 discovery survivors.
- R12 BTC/ETH volatility-compression channel breakout: CLOSED, scientific FAIL. 4/72 definitions survived frozen 2018-2022 discovery; 0 survived untouched 2023-2024 confirmation. Exact pre-2026 hashes matched; protected 2026 remained unopened.
- R13 v1.01 BTC/ETH failed-breakout rejection: CLOSED, clean scientific FAIL under the corrected staged architecture. 72 tested; 66 enough-n; 24 gross-positive; 34 gross-stable; 0 passed BH-FDR discovery; 2026 unopened. R13 v1.00 remains historical protocol-nonconforming evidence only.
- R14 Bitcoin negative-shock literature replication: CLOSED. Historical effect recovery was strong (48/48 positive; 47/48 replication pass), but 0 survived independent BH-FDR confirmation on 2021H2-2024. Protected 2026 unopened.

Historical orchestrator PASS receipts mean executor success only and do not override scientific FAIL payloads.

## Active P0 — R15 XAUUSD GLD intraday-momentum literature near-replication

R14 canonical closure:
`research/autonomous/R14_CANONICAL_CLOSURE_2026_09_13.md`

R15 base preregistration:
`research/autonomous/R15_XAUUSD_GLD_INTRADAY_MOMENTUM_PREREGISTRATION_2026_09_13.md`

R15 frozen source repair:
`research/autonomous/R15_DUKASCOPY_SOURCE_AMENDMENT_2026_09_13.md`

Cold audit:
`research/autonomous/R15_V101_COLD_AUDIT_2026_09_13.md`

External benchmark:
Xu, Bouri, Saeed & Wen (2020), Resources Policy 69, 101830, DOI 10.1016/j.resourpol.2020.101830.

Published GLD finding:
- fifth US-session half-hour return r5 positively predicts final half-hour r13;
- published beta 0.0436, Newey-West t=3.03, R-squared 0.49%;
- published GLD sample 2004-11-08 through 2019-05-30.

Critical source finding:
- FundedNext cannot support R15 published-period recovery: a read-only depth probe returned no usable in-window M1 before 2025 and no usable M5 overlapping the paper end date.
- This is infrastructure/source insufficiency, not an R15 scientific result.
- No R15 market result existed before source repair.

Reusable XAU data policy:
- the ongoing Dukascopy acquisition downloads full daily **M1** payloads, not M15;
- R15's compact study file keeps only four New York opens per eligible day, but the full daily M1 source payloads remain cached;
- after completion, the cache is to be registered as Guardian's reusable XAUUSD historical master source for the covered dates;
- future XAU studies must reuse the cache before remote redownload and derive M5/M15/M30/H1/H4/D1 locally from M1 when appropriate;
- source cache remains immutable; study-specific derivatives are written separately;
- policy: `research/autonomous/XAUUSD_DUKASCOPY_MASTER_CACHE_POLICY_2026_09_14.md`;
- registrar: `research/autonomous/register_xauusd_dukascopy_master_cache_v1_00.py`.

Canonical R15 v1.01 source:
- Dukascopy public XAUUSD BID M1 daily candle feed;
- downloader retains only exact New York 11:30, 12:00, 15:30 and 16:00 OPEN values;
- absolute Dukascopy point scale is intentionally irrelevant because R15 uses ratios/log-ratios only;
- daily compressed payload SHA256 provenance and compact-boundary SHA256 are persisted;
- 2026 URLs/rows are hard-forbidden.

Frozen chronology after source repair:
- Stage 1 full published-date near-replication: 2004-11-08 through 2019-05-30;
- Stage 2 independent confirmation: 2019-05-31 through 2024-12-31;
- Stage 3 executable/economic translation only after confirmation;
- Stage 4 pre-OOS: calendar 2025;
- protected final OOS: 2026 forbidden.

The cross-instrument limitation remains explicit: paper asset GLD, Guardian source XAUUSD.

Observed execution state:
- deterministic R15 v1.01 methodology/source preflight PASS on the user's machine;
- first remote Dukascopy source probe reached the second representative date and failed on 2010-06-01 with WinError 10054 after bounded urllib retries;
- classification: transport/infrastructure FAIL only; no R15 market result and no scientific gate evaluated.

Frozen transport repair:
`research/autonomous/R15_DUKASCOPY_TRANSPORT_REPAIR_2026_09_13.md`

Queue generation 79:
1. `R15-DUKASCOPY-TRANSPORT-PREFLIGHT r1`
2. `R15-DUKASCOPY-SOURCE-PROBE r2`
3. `R15-DUKASCOPY-BOUNDARY-EXPORT r2`
4. `R15-XAUUSD-GLD-INTRADAY-MOMENTUM-V101 r2`

Transport r2 is sequential and resumable, uses curl HTTP/1.1 primary with urllib fallback, forces connection close, caches successful compressed daily payloads atomically, and retains hard 2026 guards. The scientific engine remains unchanged.

Do not use the superseded FundedNext R15 exporter or Dukascopy transport r1. Do not substitute another half-hour if r5 fails. Any further remote-source failure remains infrastructure until an actual R15 market result exists.

## Owner-directed XAU acquisition optimization — 2026-09-14

The owner explicitly instructed Guardian to stop the healthy but excessively slow sequential Dukascopy downloader, preserve everything already acquired, determine the exact unresolved dates, anticipate two-part cache compatibility, and complete only the missing portion by a materially faster method.

Canonical transition:
- original sequential cache is frozen/immutable after stop;
- final sequential progress is snapshotted;
- exact inventory validates + hashes every original .bi5 payload and derives the unresolved date list from the frozen last_date boundary while preserving future probe files;
- known pre-freeze absent weekdays are treated as already-attempted missing/holiday dates;
- fastfill writes only to a separate cache, default 8 concurrent workers, bounded curl/urllib retries, atomic writes, explicit 404 markers, and continues past isolated transport failures;
- original and fastfill caches are never physically merged or overwritten;
- strict union builder verifies frozen original hashes, requires same-hash duplicates, requires every weekday to resolve to payload or known missing marker, then builds the R15 boundary CSV and reusable master payload index;
- protected 2026 remains forbidden;
- R15 scientific engine v1.01 is unchanged.

Cold audit:
`research/autonomous/R15_XAU_FASTFILL_TRANSITION_COLD_AUDIT_2026_09_14.md`

Transition launcher:
`research/autonomous/transition_r15_xau_to_fastfill_v1_00.ps1`

Queue generation 80 intentionally disables orchestrator execution during the manual stop/freeze transition to prevent duplicate downloaders.

## Research program — literature-first replication

After R13, do not default to another blind parameter-family sweep.

Guardian must add a literature-first replication branch:
1. Build a catalog of published market anomalies/edges with clear definitions, original sample, assets, horizon, data requirements, statistical result, and economic assumptions.
2. Prioritize phenomena that can be reproduced exactly or near-exactly from available historical data.
3. Reproduce the published phenomenon first on its original or closest feasible sample.
4. Freeze the reproduced rule before independent later-period confirmation.
5. Only after confirmation, apply realistic execution/cost robustness, then 2025 pre-OOS, then protected 2026 last.
6. No post-hoc threshold rescue of failed papers or failed Guardian families.
7. Maintain a paper-by-paper ledger: published result -> Guardian reproduction -> independent persistence -> economic robustness -> pre-OOS -> final OOS.
8. Include external/open-source EA strategies as benchmark controls where source code and rules are auditable; test them without marketing optimizations and under the same Guardian standards.
9. Use replication failures diagnostically: if Guardian cannot recover a well-specified published in-sample effect, audit data, implementation, timing, and methodology before concluding the anomaly is absent.

## Venue priority — owner decision

The owner's intended prop firms are:
- FTMO — primary long-term venue and default target for promotion;
- FundedNext — secondary venue / portability target.

FTMO should receive priority in downstream execution-fidelity work because the owner expects to use it most, especially for crypto strategies that may exploit weekend trading when the specific FTMO symbol is open.

Research must NOT assume identical tradability across FTMO and FundedNext. For each promoted candidate, maintain venue-specific execution profiles covering at least:
- eligible symbol mapping;
- actual quote/trading sessions and weekend availability;
- spread, commission and swap model;
- leverage / margin constraints;
- overnight and weekend holding restrictions by account type;
- news/event restrictions;
- platform/server-time conventions;
- symbol-specific maintenance windows and exceptional closures.

A scientific edge is venue-agnostic evidence until the economic/execution stage. A candidate may therefore PASS scientifically yet PASS FTMO and FAIL FundedNext, or vice versa. Do not collapse these outcomes into one generic cost model.

For crypto specifically, retain weekend observations in scientific datasets when economically relevant; do not strip Saturday/Sunday merely for compatibility with a weekday-only venue. Instead evaluate a weekday-only execution mask and an FTMO-compatible weekend-capable mask separately downstream. This prevents FundedNext constraints from erasing a potentially valid FTMO weekend edge during discovery.

## Asset universe — critical scope rule

Guardian is NOT restricted to BTC/ETH or crypto.

The research universe may use the full set of instruments available for trading on FTMO and FundedNext, subject to data availability and each firm's current instrument/rule constraints. This may include, where available:
- FX majors/minors;
- equity indices;
- metals such as XAU/XAG;
- energies/commodities;
- crypto instruments;
- other prop-firm-supported CFDs or futures-style products.

Asset choice must be driven by the published anomaly or economic hypothesis, not by historical convenience. BTC/ETH remain valid research assets, but they are no longer the default universe for every new family.

For every new replication/family:
- record the intended prop-firm venue/account type and eligible symbol mapping;
- verify trading hours, contract specifications, spread/commission model, news restrictions, overnight/weekend constraints and any symbol-specific rules before economic promotion;
- keep discovery/confirmation scientific logic separated from downstream prop-firm execution fidelity;
- never infer that an edge on one asset automatically transfers to another;
- do not exclude an asset solely because no local dataset exists yet: first classify the additional data required and whether it is worth acquiring.

## Research strategy correction

The main bottleneck is no longer assumed to be parameter search depth. Millions of variants around a small number of OHLCV families are not equivalent to millions of independent hypotheses.

Future work should therefore maximize:
- diversity of genuine economic/behavioral hypotheses;
- replication of independently published effects;
- cross-asset breadth when the literature supports it;
- transparent failure funnels;
- and explicit testing of Guardian itself via benchmark strategies.

Do not weaken final standards. The correction is to improve the source and diversity of hypotheses, not to lower acceptance thresholds.

## Hard rules

- Never deploy live automatically.
- Never use protected 2026 for discovery or rescue.
- Distinguish scientific FAIL from infrastructure FAIL.
- Never restart a healthy job or create duplicate revisions.
- Jobs are immutable by `(id, revision)` once run.
- After infrastructure failure, preserve the frozen scientific hypothesis and revision only the repair.
- Before every expensive phase: cold audit, deterministic tests, then execute only if the gate passes.
- No same-sample rescue of failed alpha.
- No sizing or Challenge Lab rescue.
- Codex remains out of circuit unless mandate conditions are met.
- Prefer Python; use MT5 only when broker/server/execution fidelity genuinely requires it.

## Canonical supporting documents

- `START_HERE_NEXT_AI.md`
- `GUARDIAN_MASTER_MANDATE.md`
- `docs/RESEARCH_PROTOCOL.md`
- `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md`
- `research/autonomous/DISCOVERY_GATE_ARCHITECTURE_V1.md`
- `research/autonomous/RESEARCH_QUEUE.json`
- `research/autonomous/RESEARCH_QUEUE_APPEND.json`
- `research/autonomous/R13_V101_CANONICAL_CLOSURE_2026_09_13.md`
- `research/autonomous/R14_BITCOIN_HOURLY_NEGATIVE_SHOCK_REPLICATION_PREREGISTRATION_2026_09_13.md`

Historical handoffs remain provenance only and must not override this current state.
