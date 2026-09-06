# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `research/experiments/D039.json`
4. `research/campaigns/D039_INSIDE_DAY_BREAKOUT_V0_PREREGISTRATION_2026_09_07.md`
5. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D039-INSIDE-DAY-BREAKOUT-V0**
- State: **READY_SMOKE**
- Next action: **On return to the MT5 research PC, pull the refactor branch and run `py -3 .\research\runner\guardian_research.py compile D039`. D039 is preregistered, source-complete and SHA-frozen but has not yet received local MetaEditor compile proof. If compile is 0 errors / 0 warnings with trusted EX5 receipt, run `py -3 .\research\runner\campaign.py D039 --stage smoke --no-finalize` to execute the three-market October-2023 engineering smoke and native Trade Path validation in one unattended command. Do not open D039 development until smoke passes. The assistant can read the automatically published GitHub evidence after the user says only `fini`.**

## Operational truths

- Codex required: **NO**
- Guardian Core baseline: **v12.01** — do not modify during this research refactor.
- Legacy AutoSync: **UNTRUSTED_NEVER_RELIABLY_WORKED** — reference only, never fallback.
- AutoSync target: **AUTOSYNC_V3_FROM_SCRATCH**.
- Closed experiments: D017=REJECTED_ALPHA_FAMILY, D023=REJECTED_UNTOUCHED_CONFIRMATION, D036=REJECTED_V0, D037=REJECTED_V0, D038=REJECTED_V0_COUNT_GATE_ONLY_RICH_PATH_RETAINED.

If this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:

```powershell
python research/runner/state_tools.py generate
```
