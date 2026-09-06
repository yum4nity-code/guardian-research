# START HERE — GUARDIAN

> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**
> Authoritative state: `GUARDIAN_STATE.json`.

Read only what is needed, in this order:

1. `GUARDIAN_STATE.json`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `research/experiments/D037.json`
4. `research/campaigns/D037_WILLIAMS_PREVDAY_RANGE_VOLATILITY_BREAKOUT_V0_PREREGISTRATION_2026_09_06.md`
5. `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`

## Current P0

- Experiment: **D037-WILLIAMS-PREVDAY-RANGE-VOLATILITY-BREAKOUT-V0**
- State: **REJECTED**
- Next action: **On the MT5 research PC, pull the latest branch and run exactly `py -3 .\research\runner\guardian_research.py finalize D037 --stage development`. This must not launch MT5. Require FINALIZE_PASS, rich analytics over the validated 2,377 DEV trades, a compact result bundle, and an isolated publish to the backtest-results branch (or an idempotent already-present no-op) with a local publish receipt. D037 remains REJECT_V0. After this proof, select and preregister D038 with native Trade Path telemetry.**

## Operational truths

- Codex required: **NO**
- Guardian Core baseline: **v12.01** — do not modify during this research refactor.
- Legacy AutoSync: **UNTRUSTED_NEVER_RELIABLY_WORKED** — reference only, never fallback.
- AutoSync target: **AUTOSYNC_V3_FROM_SCRATCH**.
- Closed experiments: D017=REJECTED_ALPHA_FAMILY, D023=REJECTED_UNTOUCHED_CONFIRMATION, D036=REJECTED_V0.

If this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:

```powershell
python research/runner/state_tools.py generate
```
