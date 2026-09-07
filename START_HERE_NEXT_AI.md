# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `research/experiments/D040.json`
4. `research/campaigns/D040_NR4_VOLATILITY_CONTRACTION_BREAKOUT_V0_PREREGISTRATION_2026_09_07.md`
5. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D040-NR4-VOLATILITY-CONTRACTION-BREAKOUT-V0**
- State: **READY_SMOKE**
- Next action: **On the MT5 research PC, pull the refactor branch and run `py -3 .\research\runner\guardian_research.py compile D040`. D040 is preregistered, source-complete and CI-SHA-frozen. If local MetaEditor compilation is accepted with 0 errors / 0 warnings and a trusted EX5 receipt, run `py -3 .\research\runner\guardian_research.py campaign D040 --stage smoke --no-finalize`. Smoke is engineering-only on USDJPY/XAUUSD/BTCUSD for 2023-10-02..2023-10-31. Do not inspect smoke alpha and do not open DEV until lifecycle + native Trade Path pass. After completion the user only needs to say `fini`; the assistant reads GitHub evidence.**

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
