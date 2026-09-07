# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `GUARDIAN_MASTER_MANDATE.md`
4. `research/experiments/D041.json`
5. `research/campaigns/D032_M2_DOJI_REALISTIC_MANAGEMENT_POST2024_VALIDATION_PREREGISTRATION_2026_09_05.md`
6. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D041-D032-M2-DOJI-MANAGEMENT-VALIDATION-V0**
- State: **READY_DEV**
- Next action: **On the MT5 research PC run `git pull` then `py -3 .\research\runner\d041_management_workflow.py D041 --stage development`. In D041 this runner stage name is only an orchestration label: scientifically it is the already-preregistered D032-M2 POST2024 MANAGEMENT VALIDATION, not a new development/tuning sample. The exact source and all gates remain frozen. It runs BTCUSD/ETHUSD/DOGUSD sequentially with Model=1 as preregistered, then applies the specialized paired month-block bootstrap scorer and publishes automatically. Do not inspect or modify thresholds mid-run. After completion the user should only say `fini`; the assistant reads `backtests/d041/live/latest.json` and the score/finalize events.**

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
- Closed experiments: D017=REJECTED_ALPHA_FAMILY, D023=REJECTED_UNTOUCHED_CONFIRMATION, D036=REJECTED_V0, D037=REJECTED_V0, D038=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED, D039=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED, D040=UNCONFIRMED_2026_H1_ARCHIVED, D045=REJECTED_V0_MEAN_GATE_ONLY_RICH_PATH_RETAINED.

If this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:

```powershell
python research/runner/state_tools.py generate
```
