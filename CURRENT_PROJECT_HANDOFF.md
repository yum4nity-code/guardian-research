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

Historical orchestrator PASS receipts mean executor success only and do not override scientific FAIL payloads.

## Active P0 — R14 Bitcoin hourly negative-shock literature replication

R13 is closed canonically at:
`research/autonomous/R13_V101_CANONICAL_CLOSURE_2026_09_13.md`

R14 is preregistered at:
`research/autonomous/R14_BITCOIN_HOURLY_NEGATIVE_SHOCK_REPLICATION_PREREGISTRATION_2026_09_13.md`

External benchmark:
Miralles-Quirós & Miralles-Quirós (2022), “Intraday Bitcoin price shocks: when bad news is good news”, Journal of Applied Economics 25(1), DOI 10.1080/15140326.2022.2151253.

Scientific question: can Guardian recover the paper's published positive post-shock Bitcoin return after negative hourly shocks on the closest feasible Binance sample, and does the exact frozen effect then persist on later independent data and remain executable after realistic costs?

Frozen design:
- BTCUSDT only, exact pre-2026 Binance 5m hash already pinned;
- complete H1 bars only, exactly 12 underlying M5 bars;
- 48 published negative-shock cells: filters 0.5/1/1.5/2.5/3.5/5% x horizons 1/2/3/4/5/6/12/24h;
- strict negative shock: hourly log return < -filter;
- paper-style replication uses overlapping close-to-close event returns and no costs/one-position filter;
- closest-feasible replication: 2017-08-17 through 2021-06-30;
- freeze replicated cells before independent 2021-07-01 through 2024-12-31 confirmation;
- BH-FDR 5% at replication and confirmation; no opposite-direction rescue;
- only after confirmation, translate to causal next-H1-open LONG execution with one-position replay;
- E1/STRESS round-trip costs 10/20 bps enter only at the economic stage;
- frozen 2025 pre-OOS gate;
- protected 2026 forbidden.

Queue append generation 75 contains:
1. `R14-BITCOIN-HOURLY-NEGATIVE-SHOCK-REPLICATION-PREFLIGHT r1` — deterministic cold methodology/code tests, gated on canonical R13 v1.01 FAIL evidence.
2. `R14-BITCOIN-HOURLY-NEGATIVE-SHOCK-REPLICATION r1` — executes only after preflight PASS and publishes compact result/diagnostic artifacts.

The supervisor performed an additional cold audit before queueing R14: exact 48-cell grid, strict negative-shock semantics, paper-stage cost isolation, overlapping event-study semantics, later executable one-position semantics, fixed chronology, pinned input hash and protected-2026 guards all passed. The deterministic synthetic preflight also passed locally before commit.

If either R14 job is running or waiting normally, do not interfere or notify the owner. On terminal R14 result, first distinguish (a) failure to reproduce the published paper effect, which requires implementation/data-source audit, from (b) successful paper replication but later persistence/economic failure. R14 PASS is pre-OOS evidence only, not an EA or live authorization.

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
