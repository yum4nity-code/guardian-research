# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `GUARDIAN_MASTER_MANDATE.md`
4. `research/experiments/D044.json`
5. `research/campaigns/D044_TURTLE_SOUP_20D_FAILED_BREAK_REVERSAL_V0_PREREGISTRATION_2026_09_07.md`
6. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D044-TURTLE-SOUP-20D-FAILED-BREAK-REVERSAL-V0**
- State: **READY_SMOKE**
- Next action: **Run D044 engineering smoke only: git pull then py -3 .\research\runner\guardian_research.py campaign D044 --stage smoke --no-finalize. Smoke is October 2023 on USDJPY, XAUUSD and BTCUSD and is engineering-only. The campaign must compile the frozen source, run Model0 sequentially, validate lifecycle and native Trade Path, and auto-publish evidence. Do not interpret smoke profitability. If smoke passes, move the unchanged source to the frozen 2024-2025 development stage.**

## Canonical operator UX

- Prefer one short PowerShell command block.
- The runner publishes results automatically to `backtest-results`.
- The user normally responds only **`fini`**.
- The assistant then retrieves GitHub evidence, updates state, and gives the next minimal command.
- Do not ask the user to paste logs/JSON when automatic transport succeeded.

## Operational truths

- Codex required: **NO**
- Guardian Core baseline: **v12.01** — do not modify during this research refactor.
- Legacy AutoSync: **UNTRUSTED_NEVER_RELIABLY_WORKED** — reference only, never fallback.
- AutoSync target: **AUTOSYNC_V3_FROM_SCRATCH**.
- Closed experiments: D017=REJECTED_ALPHA_FAMILY, D023=REJECTED_UNTOUCHED_CONFIRMATION, D036=REJECTED_V0, D037=REJECTED_V0, D038=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED, D039=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED, D040=UNCONFIRMED_2026_H1_ARCHIVED, D041=REJECTED_MANAGEMENT_D032_M2_POST2024, D045=REJECTED_V0_MEAN_GATE_ONLY_RICH_PATH_RETAINED, D046=INCONCLUSIVE_COUNT_CLOSED_NO_CONFIRMATION_STRONGLY_NEGATIVE_UNCONDITIONAL_SCREEN.

If this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:

```powershell
python research/runner/state_tools.py generate
```
