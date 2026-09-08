# START HERE — NEXT GUARDIAN AI

You are taking over the Guardian project.

## Current P0

The active research campaign is now **Autonomous Phenomenon Discovery on XAUUSD**.

Current sequence:

**Phase I-A news mask PASS → Phase I-B XAUUSD clean dataset → autonomous XAU phenomenon discovery → robustness/confirmation → frozen candidate only → protected 2026 final OOS with explicit owner approval.**

Read in this exact order before coding:

1. `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md`
2. `research/autonomous/RESEARCH_QUEUE.json`
3. `handoff/PHENOMENON_DISCOVERY_CURRENT_HANDOFF_2026_09_08.md`
4. latest relevant `backtest-results` `LATEST.json`
5. `GUARDIAN_MASTER_MANDATE.md`
6. `CURRENT_PROJECT_HANDOFF.md`
7. `docs/RESEARCH_PROTOCOL.md`

## Autonomous-control rules

- ChatGPT is the scientific supervisor: read evidence, preregister the next experiment, write code, update the autonomous queue.
- The local Guardian Research Orchestrator is the deterministic executor. It must not invent hypotheses.
- Prefer Python for research/backtests; use MT5 for broker/server data and later execution-fidelity confirmation.
- Jobs are immutable by `(id, revision)` once run.
- Long jobs use heartbeat/progress plus adaptive timeout; do not kill a job merely because it is slow.
- Codex is disabled by default and reserved for tightly scoped code blockers after deterministic repair attempts fail.
- Normal research PASS/FAIL churn should continue without involving the owner.

## Scientific invariants

- 2024/2025 are discovery/internal confirmation only.
- **2026 remains sealed final OOS. Do not open it without explicit owner approval plus committed preregistration.**
- BTC/ETH 5m directional research families A-H are closed after repeated 2024→2025 failure. Do not same-sample rescue them.
- Phase C's low-movement/no-trade result remains the only robust practical output retained from BTC/ETH.
- Current pivot is XAUUSD with conservative high-impact USD news exclusion.
- For Phase I-A / I-B, use the one and only MT5 session already open on the owner's PC as canonical terminal/server/data source.
- Launchers/results must publish to GitHub. The owner must not be used as a log courier.
- If the owner says `published`, `fini`, `résultat ?`, etc., inspect GitHub directly.

Historical handoffs mentioning D023 or another older alpha P0 are superseded by this file and the autonomous mandate.
