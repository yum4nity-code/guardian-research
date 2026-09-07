# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / D052 MANAGEMENT-AS-ALPHA PAIRED NULL LAB READY LOCAL SMOKE+DEV**

## Read this first on a new chat

This is the freshest human-readable handoff.

Then read:
1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `research/campaigns/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_ENTRY_V0_PREREGISTRATION_2026_09_07.md`
4. `research/experiments/D052.json`
5. `research/runner/d052_management_alpha_run.py`
6. `research/runner/d052_management_alpha_workflow.py`
7. `reports/research/D051_NR7_INDEX_CLUSTER_CONFIRMATION_CLOSEOUT_20260907.md`
8. `reports/research/D041_D032_M2_POST2024_MANAGEMENT_VALIDATION_CLOSEOUT_20260907.md`
9. `GUARDIAN_MASTER_MANDATE.md`

`GUARDIAN_STATE.json`, `START_HERE_NEXT_AI.md` and `CURRENT_QUEUE.json` have now been reconciled to D052. The authoritative state and this handoff agree on the active experiment and operator action.

## Canonical operator UX

- Assistant prepares GitHub, preregistration, source identity, runner/state changes and interpretation.
- Give one short PowerShell block whenever local MT5 execution is needed.
- Runner publishes evidence automatically to `backtest-results`.
- User normally replies only **`fini`**.
- On `fini`, retrieve GitHub evidence directly; do not ask the user to paste logs/JSON if transport worked.
- If transport fails but valid local evidence exists, repair publication rather than rerunning MT5.
- Keep MT5 sequential.

## Hard boundaries

- Guardian Core v12.01 is the frozen compile-validated production baseline; do not modify during research unless explicitly asked.
- Do not merge to `main` unless explicitly requested/reviewed.
- Never `git reset --hard` or destructive-clean unrelated work.
- Legacy AutoSync v1/v2 and Guardian Backtest Bot are historical/untrusted; never fallback.
- No post-hoc rescue, no retuning after opened results, no relabeling seen data as OOS.

## Prior conclusion motivating D052

D051 NR7 equity-index cluster failed its untouched 2026-H1 confirmation:
- n61
- mean -0.0429737R/trade
- PF 0.878433
- total -2.621396R
- 2/4 symbols positive
- integrity 0
- verdict `D051_UNCONFIRMED_CLOSE`

D041 previously showed that a sophisticated management candidate materially degraded an already-confirmed D032 entry edge: paired delta -0.3380537662R/trade, -26.03014R total, 0/3 symbols improved, bootstrap interval entirely negative. Management Benchmark V1/V2 also found no universal management promotion.

The user explicitly raised the stronger belief: **“a good management can save almost any signal.”** D052 tests that belief directly instead of continuing to debate it.

## Current P0 — D052 Management-as-Alpha Paired Null-Entry Lab V0

Experiment ID:
`D052-MANAGEMENT-AS-ALPHA-PAIRED-NULL-ENTRY-V0`

Preregistration:
`research/campaigns/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_ENTRY_V0_PREREGISTRATION_2026_09_07.md`
Git blob: `faa986bb7460806ccc7b5423ba8a697f7569de8e`

Permanent manifest:
`research/experiments/D052.json`

Frozen source:
`research/strategies/d052/D052_ManagementAsAlpha_PairedNull_M15_v1_00.mq5`
Git blob: `98ca64ebe2c8e21f2579e9f4cc804b8848d6325b`
Normalized source SHA measured by GitHub CI before local MT5 execution:
`009a4bc7a5995d5d766fe6b5bec7d61b486e88d61fad0d75b29b227fb6098275`

Operator entrypoint:
`research/runner/d052_management_alpha_run.py`

Core workflow/scorer:
`research/runner/d052_management_alpha_workflow.py`

### Null-entry construction

Each eligible broker day/symbol gets one price-independent deterministic schedule minute from `symbol + broker-day key`, in 10:00–13:59 broker time. At the first executable tick at/after that minute (no later than 15:00), the harness opens **simultaneous virtual LONG and SHORT sleeves** on exactly the same event.

LONG enters ASK and liquidates BID; SHORT enters BID and liquidates ASK. No order is sent.

Because both directions exist at each event, directional drift alone cannot satisfy D052’s separate LONG-positive and SHORT-positive gates.

`1R` is ATR14 from prior completed D1 bars only. It is a volatility scale, not an entry signal.

### Frozen 12-market universe

EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF,
SPX500, NDX100, GER30, US30, XAUUSD, XAGUSD.

XPTUSD was excluded before D052 due the repeated D049 reference-engineering defect. Crypto was excluded in V0 to avoid mixing 24/7 sessions and different cost mechanics into the first null-management test.

### Frozen management family

Reference, not eligible for selection:
- `REF_EOD_NO_STOP`

Eleven candidates:
- `SL1_EOD`
- `SL1_TP1`
- `SL1_TP2`
- `SL1_TP3`
- `SL1_BE_AFTER_1R_EOD`
- `SL1_BE_AFTER_2R_EOD`
- `SL1_P50_AT_1R_BE_REST`
- `SL1_P40_AT_2_5R_BE_REST`
- `SL1_TRAIL1_AFTER_1R`
- `SL1_TRAIL1_5_AFTER_2R`
- `SL1_P50_AT_1R_TRAIL1_REST`

One MT5 run per symbol simulates reference + all 11 candidates over the identical paired entries. Therefore DEV is **12 MT5 runs, not 132**.

### Smoke

2023-10-02 through 2023-10-31, engineering-only:
- EURUSD
- SPX500
- XAUUSD

The runner requires exact 2 sides × 12 management rows for every paired event, complete lifecycle, nonzero events, zero invalid price/risk/PnL, and no duplicate event-side-management rows.

If smoke fails, DEV does not run.

### Development

2024-01-02 through 2025-12-31, all 12 markets.

All candidates are compared on the exact same entry-side events and paired against `REF_EOD_NO_STOP`.

Frozen all-required candidate gates include:
- n >=8000 legs
- each symbol n >=600
- mean net R >0
- PF >=1.05
- total and 1.5x commission-stress total >0
- LONG mean >0 and SHORT mean >0
- >=9/12 symbols positive
- 2024 >0 and 2025 >0
- paired candidate-minus-reference mean >0
- month-block bootstrap 95% lower bound absolute mean >0
- month-block bootstrap 95% lower bound paired delta >0
- max positive-symbol contribution share <=25%
- integrity 0

If zero candidates pass all gates: `D052_NO_MANAGEMENT_ALPHA_IN_FROZEN_FAMILY`; no “best loser” advances.

If one or more pass, exactly one is mechanically selected under the preregistered lexicographic rule. This first command still **does not open confirmation automatically**.

### Locked holdout

2026-07-01 through 2026-08-31, same 12 symbols.

It stays unopened unless exactly one DEV-selected candidate passes every frozen gate. A future holdout runner must expose only reference + selected candidate; outcomes for losing candidates must never be generated on holdout.

## Tooling / transport safeguards

- `d052_management_alpha_run.py` preflights the permanent manifest, prereg Git blob, source Git blob and normalized source SHA before execution.
- Workflow publishes `d052-source-freeze` before any MT5 outcome.
- MetaEditor compile is run locally before smoke.
- Smoke and DEV remain sequential MT5.
- Results publish through isolated-clone `result_transport.py`, never legacy AutoSync.
- If compile/smoke/DEV/scoring raises, the resilient entrypoint attempts to publish `d052-workflow-incomplete` so a future assistant can diagnose GitHub evidence rather than asking the operator to replay already-valid MT5 work.
- The DEV scorer applies all 16 frozen gates, deterministic month-block bootstrap and the preregistered lexicographic candidate selection.
- The D052 DEV command contains no holdout execution path; even a passing candidate leaves Jul-Aug 2026 locked for a separate reviewed runner.

Authoritative-state/active-D052 CI run `34133920148` for commit `fe74565986fd948d0ee9fa1f4d5a63fab3c11bfa` completed **SUCCESS**. It validated generated state views, D052 manifest readiness, `runner.plan('D052')`, frozen source identity and the regression suite.

## Next operator action

Run exactly:

```powershell
git pull
py -3 .\research\runner\d052_management_alpha_run.py
```

This is intentionally a large unattended block: source freeze -> compile -> 3-symbol engineering smoke -> if clean, 12-symbol 2024-2025 DEV -> paired scorer -> automatic GitHub publication.

Then the user should normally reply only:

`fini`

On `fini`, fetch `backtests/d052/live/latest.json` from `backtest-results` and the referenced event. If status is a DEV score, inspect every candidate and frozen gate. Do **not** open Jul-Aug holdout unless the score mechanically selected exactly one candidate after all gates passed.

## Local paths

Repo: `D:\MT5_Backtests\guardian-research`
Runner workspace: `D:\MT5_Backtests\guardian-runner`
FundedNext MT5: `D:\MT5_FundedNext`
MetaEditor: `D:\MT5_FundedNext\MetaEditor64.exe`
Terminal: `D:\MT5_FundedNext\terminal64.exe`
Experts: `D:\MT5_FundedNext\MQL5\Experts\GuardianResearch`
FILE_COMMON: `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\Common\Files`

## Style

Concise, direct, technically opinionated when evidence supports it. Distinguish fact, inference and unknown. Contradict the user when evidence warrants it. Do not manufacture optimism.
