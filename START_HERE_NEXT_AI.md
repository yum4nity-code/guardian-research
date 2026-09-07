# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `GUARDIAN_MASTER_MANDATE.md`
4. `research/experiments/D040.json`
5. `research/campaigns/D040_NR4_VOLATILITY_CONTRACTION_BREAKOUT_V0_PREREGISTRATION_2026_09_07.md`
6. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D040-NR4-VOLATILITY-CONTRACTION-BREAKOUT-V0**
- State: **CLOSED_UNCONFIRMED_ANALYTICS_RECOVERY_READY**
- Next action: **On the research PC run `git pull` then `py -3 .\research\runner\guardian_research.py finalize D040 --stage confirmation`. This command MUST NOT launch MT5: D040 is already scientifically CLOSED / UNCONFIRMED from the valid 191-trade 2026 H1 batch and frozen score. It only regenerates the same frozen confirmation verdict from existing evidence, computes the previously-missing descriptive rich analytics with rich_score_v2, and publishes the archival bundle. Do not rescue or retune D040. After completion the user should only say `fini`; the assistant reads GitHub and then removes D040 from the active queue.**

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
- Closed experiments: D017=REJECTED_ALPHA_FAMILY, D023=REJECTED_UNTOUCHED_CONFIRMATION, D036=REJECTED_V0, D037=REJECTED_V0, D038=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED, D039=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED.

If this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:

```powershell
python research/runner/state_tools.py generate
```
