# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `GUARDIAN_MASTER_MANDATE.md`
4. `research/experiments/D052.json`
5. `research/campaigns/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_ENTRY_V0_PREREGISTRATION_2026_09_07.md`
6. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D052-MANAGEMENT-AS-ALPHA-PAIRED-NULL-ENTRY-V0**
- State: **CLOSED_NO_MANAGEMENT_ALPHA**
- Next action: **D052 is closed. Do not open its Jul-Aug 2026 holdout and do not retune its management family. Return priority to entry/context alpha. Prepare the next fresh preregistered entry-alpha experiment before any new MT5 outcome; management remains risk/execution engineering, not an assumed source of edge.**

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
- Closed experiments: D017=REJECTED_ALPHA_FAMILY, D023=REJECTED_UNTOUCHED_CONFIRMATION, D036=REJECTED_V0, D037=REJECTED_V0, D038=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED, D039=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED, D040=UNCONFIRMED_2026_H1_ARCHIVED, D041=REJECTED_MANAGEMENT_D032_M2_POST2024, D044=REJECT_V0_STRONGLY_NEGATIVE, D045=REJECTED_V0_MEAN_GATE_ONLY_RICH_PATH_RETAINED, D046=INCONCLUSIVE_COUNT_CLOSED_NO_CONFIRMATION_STRONGLY_NEGATIVE_UNCONDITIONAL_SCREEN, D047=MARKET_TRANSPORT_NO_BROAD_PASS_NR7, D048=MARKET_TRANSPORT_NO_BROAD_PASS_INSIDE_DAY, D049=MARKET_TRANSPORT_ENGINEERING_INCOMPLETE_XPTUSD_OPERATIONALLY_CLOSED, D050=MARKET_TRANSPORT_COMPARATOR_NO_BROAD_PASS_NR4, D051=UNCONFIRMED_2026_H1_NR7_INDEX_CLUSTER, D052=NO_MANAGEMENT_ALPHA_IN_FROZEN_FAMILY.

If this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:

```powershell
python research/runner/state_tools.py generate
```
