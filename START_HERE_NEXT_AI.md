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
- State: **READY_SMOKE**
- Next action: **On the MT5 research PC, pull the latest refactor branch and run exactly `py -3 .\research\runner\guardian_research.py test-one D038 --stage smoke --symbol USDJPY`. This is one engineering-only smoke run for 2023-11-01 through 2023-11-30 under Model=0. Require TEST_PASS_INTEGRITY, FINAL lifecycle, opened=closed=rows, zero invalid price/risk/PnL/path failures, and usable native Trade Path telemetry before running the three-symbol smoke batch.**

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
