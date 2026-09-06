# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `research/experiments/D038.json`
4. `research/campaigns/D038_NR7_VOLATILITY_CONTRACTION_BREAKOUT_V0_PREREGISTRATION_2026_09_06.md`
5. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D038-NR7-VOLATILITY-CONTRACTION-BREAKOUT-V0**
- State: **COMPILE_PENDING**
- Next action: **On the MT5 research PC, pull the latest refactor branch and run only `py -3 .\research\runner\guardian_research.py compile D038`. Require COMPILE_PASS with 0 errors / 0 warnings and an EX5 SHA before any D038 backtest. If compile passes, the next separate proof is exactly one USDJPY smoke test for 2023-11-01 through 2023-11-30 using Model=0; do not launch the three-symbol smoke batch until that single run passes lifecycle and Trade Path integrity.**

## Operational truths

- Codex required: **NO**
- Guardian Core baseline: **v12.01** — do not modify during this research refactor.
- Legacy AutoSync: **UNTRUSTED_NEVER_RELIABLY_WORKED** — reference only, never fallback.
- AutoSync target: **AUTOSYNC_V3_FROM_SCRATCH**.
- Closed experiments: D017=REJECTED_ALPHA_FAMILY, D023=REJECTED_UNTOUCHED_CONFIRMATION, D036=REJECTED_V0, D037=REJECTED_V0.

If this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:

```powershell
python research/runner/state_tools.py generate
```
