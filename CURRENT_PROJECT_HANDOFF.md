# Guardian Research — CURRENT PROJECT HANDOFF

## Canonical current state — 2026-09-13

Read `START_HERE_NEXT_AI.md`, this file, the durable mandates, the current queue append, and latest `backtest-results` evidence before acting.

## Closed evidence

- R4 close-to-close XAU family: CLOSED after causal-capture forensic work.
- R5 causal-next-open XAU family: CLOSED for tradable-alpha promotion after pre-OOS economic robustness scientific FAIL, 0/96 under inherited costs.
- R8 BTC/ETH relative-value mean reversion: CLOSED, scientific FAIL, 0/54 discovery survivors.
- R9 BTC/ETH UTC calendar/session seasonality: CLOSED, scientific FAIL, 0/672 discovery survivors. Published `phenomenon-discovery/r9-btc-eth-calendar-session/LATEST.json`; exact pre-2026 BTC/ETH input hashes matched and protected 2026 remained unopened.

Historical orchestrator PASS receipts mean executor success only and do not override scientific FAIL payloads.

## Active P0 — R10 independent BTC/ETH multi-day trend family

R10 is preregistered at:
`research/autonomous/R10_BTC_ETH_MULTI_DAY_TREND_PREREGISTRATION_2026_09_13.md`

Scientific question: can simple low-turnover multi-day BTC/ETH time-series momentum survive long-history discovery, independent confirmation, 2025 pre-OOS and fixed 10/20 bps round-trip costs using causal next-H1-open execution?

Frozen design:
- existing BTCUSDT/ETHUSDT spot 5m 2017-2025 files with exact SHA256 values pinned from terminal R9 evidence;
- complete H1 construction only, exactly 12 underlying M5 bars;
- 72 deterministic definitions: 2 assets x lookback 24/72/168/336 h x absolute momentum threshold 1/2/4% x holding 24/72/168 h;
- decision once daily from completed 00:00 UTC H1 bar, entry at next H1 open;
- one-position chronological replay; missing-hour fail closed; cross-year trades purged;
- discovery 2018-2022; freeze IDs before confirmation;
- confirmation 2023-2024 with BH-FDR 5%; freeze IDs before 2025;
- 2025 pre-OOS gate with H1/H2, ex-best-trade and concentration rejection;
- protected 2026 forbidden.

Queue append generation 71 contains:
1. `R10-BTC-ETH-MULTI-DAY-TREND-PREFLIGHT r1` — deterministic cold tests, gated on terminal R9 scientific FAIL.
2. `R10-BTC-ETH-MULTI-DAY-TREND r1` — executes only after preflight PASS and verifies exact input hashes internally.

If either R10 job is running or waiting normally, do not interfere or notify the owner. On terminal R10 result, verify provenance/integrity before any next action. R10 PASS is pre-OOS evidence only, not an EA or live authorization.

## Hard rules

- Never deploy live automatically.
- Follow the canonical protected-OOS policy in `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md`; no opportunistic 2026 access.
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
- `research/autonomous/RESEARCH_QUEUE.json`
- `research/autonomous/RESEARCH_QUEUE_APPEND.json`
- `research/autonomous/R10_BTC_ETH_MULTI_DAY_TREND_PREREGISTRATION_2026_09_13.md`

Historical handoffs remain provenance only and must not override this current state.
