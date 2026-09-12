# Guardian Research — CURRENT PROJECT HANDOFF

## Canonical current state

Read this file first. The detailed current continuity snapshot is:

`handoff/2026/09/11/GUARDIAN_R4_R5_CURRENT_HANDOFF_2026_09_11.md`

That dated handoff is the canonical source for the current R4/R5 research state.

## Current live research state — 2026-09-11

- R4 causal-capture forensic audit: **PASS_INTERPRETABLE**.
- R4 close-to-close family: **CLOSED**.
- Main finding: about **99.5% of the B→C degradation is ENTRY_DELTA**, meaning most of the apparent R4 edge was realized before the first executable entry reference.
- R5 causal-next-open r2 is **complete: PASS**, with **5,661 discovery candidates and 96 frozen 2025-confirmed survivors** after HAC/BH-FDR, four-quarter positivity and adjacent-quantile robustness.
- R5 post-result cold audit r3 is **PASS_INTERPRETABLE**: exact R5 hash matched, all four canonical Phase I-B hashes matched, **0 material semantic changes**, **0 provenance failures**, protected 2026 unopened.
- The next authorized step is a **reject-only pre-OOS economic robustness screen** on the frozen 96, using first-available raw-M1 execution and inherited E1/STRESS cost gates on 2024/2025 only.
- Queue is now **generation 51**. Economic r1 was superseded before execution only to add bounded retry/backoff around atomic JSON writes for the workstation's known transient Windows PermissionError. Scientific logic/gates are unchanged.
- Enabled next jobs: `R5-PRE-OOS-ECONOMIC-ROBUSTNESS-PREFLIGHT r2` then `R5-PRE-OOS-ECONOMIC-ROBUSTNESS r2`.
- Protected 2026 remains forbidden. A PASS here is still not an EA and does not authorize OOS.
- Do not use Codex for this workflow unless the operator explicitly changes that decision.
- Do not deploy live.
- Do not open protected 2026 OOS without explicit owner approval and preregistration.

## Immediate resume procedure

1. Read `handoff/2026/09/11/GUARDIAN_R4_R5_CURRENT_HANDOFF_2026_09_11.md`.
2. Inspect the local R5 progress file:
   `D:\MT5_Backtests\Research\Autonomous\progress\STRATEGY-FACTORY-R5-CAUSAL-NEXT-OPEN-R2.json`
3. Inspect:
   `D:\MT5_Backtests\Research\Autonomous\orchestrator_health.json`
4. Inspect the `backtest-results` branch for the final R5 r2 receipt/publication.
5. If R5 is still running normally: do not interfere.
6. If R5 is complete: perform the mandatory cold methodology/code/provenance audit described in the dated handoff before any new phase.
7. If R5 failed: classify scientific vs infrastructure failure before deciding what to do.

## Canonical supporting documents

- `GUARDIAN_MASTER_MANDATE.md` — durable project rules and architecture.
- `docs/RESEARCH_PROTOCOL.md` — scientific research discipline.
- `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md` — autonomous executor/supervisor contract.
- `research/autonomous/RESEARCH_QUEUE.json` and `RESEARCH_QUEUE_APPEND.json` — executable queue state.
- `docs/REPO_MAP.md` — repository navigation and archive conventions.
- `README.md` — repository purpose and general operating rules.

## Historical material

Older campaign state, D0xx histories, prior handoffs, Codex exchanges and superseded research notes remain preserved for provenance but are **not current state** unless explicitly referenced by the current dated handoff.

The previous accumulated version of this file was archived at:

`handoff/archive/CURRENT_PROJECT_HANDOFF_LEGACY_THROUGH_2026_09_11.md`

Use historical material as evidence, not as the current instruction source.
