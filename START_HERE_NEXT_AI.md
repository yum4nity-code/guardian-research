# START HERE — GUARDIAN

> Current compatibility entrypoint for the active research session.

## Read in this order

1. `CURRENT_PROJECT_HANDOFF.md`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `reports/research/MARKET_TRANSPORT_LAB_V1_CLOSEOUT_20260907.md`
4. `research/campaigns/D051_NR7_EQUITY_INDEX_CLUSTER_CONFIRMATION_V0_PREREGISTRATION_2026_09_07.md`
5. `research/runner/d051_nr7_index_confirmation.py`
6. `GUARDIAN_MASTER_MANDATE.md`
7. `GUARDIAN_STATE.json`

## Current P0

**D051 — NR7 Equity-Index Cluster Confirmation V0**

Frozen symbols: SPX500, NDX100, GER30, US30.

Untouched confirmation window: 2026-01-02 through 2026-06-30.

Next operator command:

```powershell
git pull
py -3 .\research\runner\d051_nr7_index_confirmation.py
```

Then the user normally replies only:

`fini`

The assistant retrieves `backtests/d051/live/latest.json` from branch `backtest-results` and continues autonomously.

## Canonical operator UX

- Prefer one short PowerShell block.
- Results auto-publish to `backtest-results`.
- Do not ask the user to paste logs/JSON when automatic transport succeeded.
- If transport fails but local evidence is valid, repair publication instead of rerunning MT5.
- MT5 remains sequential.

## Scientific boundary

Market Transport Lab V1 is closed with no broad transport pass. D051 is a **new** asset-class hypothesis generated from the D047 discovery that all four equity indices were positive in 2024-2025. D051 does not rescue D038 or D047.

D051 H1 gates are frozen in its preregistration. If any gate fails, D051 closes with no symbol removal or retuning. If every gate passes, only then may the already-reserved 2026-07-01 through 2026-08-31 holdout be opened.

## Operational truths

- Codex required: NO.
- Guardian Core baseline: v12.01; do not modify during this research flow.
- Legacy AutoSync v1/v2 and Guardian Backtest Bot are historical/untrusted; never fallback.
- Current result transport is `research/runner/result_transport.py` using isolated Git clones.
- Never `git reset --hard`.
- Do not merge to `main` unless explicitly requested/reviewed.

## State note

`GUARDIAN_STATE.json` still contains stale D044-era active fields. Until that structural state file is reconciled, `CURRENT_PROJECT_HANDOFF.md`, this file, the D051 preregistration and `backtest-results` are the current active-session evidence. Historical details in `GUARDIAN_STATE.json` remain useful.
