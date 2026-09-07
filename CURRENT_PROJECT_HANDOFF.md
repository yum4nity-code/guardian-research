# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **D052 CLOSED / RETURN TO ENTRY-CONTEXT ALPHA RESEARCH**

## Read this first on a new chat

Read in this order:
1. `GUARDIAN_STATE.json`
2. `reports/research/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_CLOSEOUT_20260907.md`
3. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
4. `research/experiments/D052.json`
5. `research/campaigns/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_ENTRY_V0_PREREGISTRATION_2026_09_07.md`
6. `reports/research/D051_NR7_INDEX_CLUSTER_CONFIRMATION_CLOSEOUT_20260907.md`
7. `reports/research/D041_D032_M2_POST2024_MANAGEMENT_VALIDATION_CLOSEOUT_20260907.md`
8. `GUARDIAN_MASTER_MANDATE.md`

`GUARDIAN_STATE.json`, `START_HERE_NEXT_AI.md` and `CURRENT_QUEUE.json` are authoritative/current.

## Canonical operator UX

- Assistant prepares GitHub/state/research tooling.
- Give one short PowerShell block only when local MT5 is required.
- Runner publishes evidence automatically to `backtest-results`.
- User normally replies only **`fini`**.
- On `fini`, fetch GitHub evidence directly; do not ask for pasted logs if transport worked.
- Transport failure alone never justifies replaying valid MT5 work.
- Keep MT5 sequential.

## Hard boundaries

- Guardian Core v12.01 remains frozen compile-validated production baseline.
- Do not merge to `main` unless explicitly requested/reviewed.
- Never `git reset --hard` or destructively clean unrelated work.
- Legacy AutoSync v1/v2 and Guardian Backtest Bot are untrusted historical systems; never fallback.
- No post-hoc rescue, threshold retune, symbol deletion after results, or reuse of seen data as OOS.

## D052 formal closeout

Experiment:
`D052-MANAGEMENT-AS-ALPHA-PAIRED-NULL-ENTRY-V0`

Authoritative result:
`backtests/d052/live/events/development/d052-development-score/20260907T152924Z`

Formal status:
`D052_NO_MANAGEMENT_ALPHA_IN_FROZEN_FAMILY`

Result:
- passing management candidates: **0 / 11**
- selected candidate: **none**
- integrity events: **0**
- Jul-Aug 2026 holdout: **UNOPENED / permanently locked by failed DEV**

Reference null entry:
- n = 12,318 legs
- mean = -0.0266264853R
- total = -327.98504593R
- PF = 0.8790507722

Least-negative candidate by mean: `SL1_BE_AFTER_1R_EOD`
- mean = -0.0249931593R
- total = -307.86573628R
- stress total = -357.25723913R
- PF = 0.8847298470
- LONG mean = -0.0122215542R
- SHORT mean = -0.0377647644R
- paired lift versus reference = +0.0016333260R/leg
- paired-delta month-block bootstrap lower 95% = -0.0029910883R

Interpretation: the best management reduced the descriptive loss slightly, but remained strongly negative and did not demonstrate robust incremental alpha. No candidate justified holdout.

Scientific conclusion: **management can reshape the distribution, but this frozen family did not manufacture alpha from a price-independent direction-neutral entry. Entry/context alpha remains necessary.**

Closeout:
`reports/research/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_CLOSEOUT_20260907.md`

## Prior management evidence

- D041: confirmed D032 Bullish Doji Star entry reference remained strong, but the frozen realistic management candidate degraded it by -0.3380537662R/event; bootstrap delta entirely negative.
- Management Benchmark V1/V2: no universal management promotion across D038/D039/D040/D045 paths.
- D052 now directly rejects the stronger claim that ordinary fixed SL/TP/BE/partial/trailing combinations can reliably rescue an information-free entry.

Management is still essential for account-risk control and execution, but should not be treated as the assumed source of expectancy.

## Current P0

Return to **fresh entry/context alpha**.

Do not spend more cycles on generic management variants now. Do not reopen D052 holdout. Do not broadly rerun D017 Momentum or raw RSI families without a genuinely new preregistered hypothesis; prior evidence is already broad and negative.

The next experiment should:
- come from a documented, clearly distinct entry family;
- have predictable trade frequency;
- freeze the market universe before outcomes;
- use realistic FundedNext execution/costs;
- use 2024-2025 DEV and an untouched later confirmation where available;
- keep management deliberately minimal so entry alpha is measured cleanly.

A high-priority candidate for design is a **session-based Opening Range Breakout benchmark on liquid indices**, because it is structurally distinct from D1 contraction/Donchian/failed-break families and naturally produces enough events for robust testing. This is a design direction only until exact rules, session handling, universe, source and gates are preregistered.

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
