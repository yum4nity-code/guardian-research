# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / D053 US-INDEX ORB30 READY LOCAL SMOKE+DEV**

## Read this first on a new chat

Read in this order:
1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `research/campaigns/D053_US_INDEX_ORB30_ENTRY_ALPHA_V0_PREREGISTRATION_2026_09_07.md`
4. `research/experiments/D053.json`
5. `research/runner/d053_orb30_index_run.py`
6. `research/runner/d053_orb30_index_workflow.py`
7. `reports/research/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_CLOSEOUT_20260907.md`
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

## Why D053 exists

D052 directly tested the user's strong management hypothesis on 12,318 price-independent LONG/SHORT legs and 11 frozen management rules. Result: 0/11 passed; the least-negative management remained negative and its incremental bootstrap included zero. D052 is permanently closed and its Jul-Aug 2026 holdout stays unopened.

Research priority therefore returns to entry/context alpha.

## Current P0 — D053 US Index ORB30 Entry Alpha V0

Experiment:
`D053-US-INDEX-ORB30-ENTRY-ALPHA-V0`

Preregistration:
`research/campaigns/D053_US_INDEX_ORB30_ENTRY_ALPHA_V0_PREREGISTRATION_2026_09_07.md`
Git blob:
`2d66799b1e25cc6cf19dd5d033bd2731372c5cd3`

Frozen source:
`research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5`
Git blob:
`f60329c6fcb79b308c5a60e74c0512b52481386a`
Normalized SHA256:
`bbd0178f3c71a99802b75db563f06f38a94d4735bc828a78ee8c009dd4900ec8`

Operator entrypoint:
`research/runner/d053_orb30_index_run.py`

Workflow/scorer:
`research/runner/d053_orb30_index_workflow.py`

### Frozen universe

- SPX500
- NDX100
- US30
- US2000

No additions/removals after results.

### Frozen rule

FundedNext server time:
- build executable ASK/BID opening range from **16:30:00 through 16:59:59**;
- from 17:00, first executable break by **1 trade tick** wins;
- LONG enters ASK above OR ask-high; SHORT enters BID below OR bid-low;
- one trade/symbol/day; no reversal/re-entry;
- initial stop at opposite executable OR extreme;
- no TP, BE, trail, partial, trend/volatility/weekday/volume filter;
- structural stop or first executable liquidation at/after **22:45**.

The fixed server-time anchor is the actual tested rule. It is an operational proxy for the US cash-open region, not a claim of perfect exchange-local alignment during DST transition mismatch days.

Primary costs use executable spread. Frozen stress applies an additional 0.5x observed round-trip spread penalty to represent **1.5x spread stress**.

Native path exports MFE/MAE and timing for later descriptive analysis only.

### Smoke

2023-10-02 through 2023-10-31:
- SPX500
- NDX100
- US2000

Engineering-only. No profitability interpretation.

If compile or smoke integrity fails, DEV must not run.

### Development

2024-01-02 through 2025-12-31, all four symbols.

All frozen gates required:
- n >=1000;
- each symbol n >=200;
- mean >= +0.050R/trade;
- PF >=1.10;
- total >0;
- 1.5x spread-stress total >0;
- >=3/4 symbols positive;
- 2024 >0 and 2025 >0;
- month-block bootstrap lower 95% >0;
- max positive-symbol contribution share <=55%;
- integrity 0.

LONG/SHORT attribution is reported but is not a gate and cannot be post-hoc selected to rescue D053.

Failure: `D053_REJECT_V0`.
Pass: `D053_DEV_PASS_HOLDOUT_LOCKED`.

### Holdout

2026-07-01 through 2026-08-31 remains **LOCKED / UNOPENED** in the smoke+DEV command.

2026 H1 is not reused as untouched confirmation because prior index experiments already exposed it.

A future confirmation command may be created only if every DEV gate passes.

## Tooling safeguards

- source/prereg blob identities verified locally before execution;
- normalized source SHA verified;
- MetaEditor compile required before smoke;
- Model0 / Every tick;
- stale FILE_COMMON outputs quarantined;
- lifecycle, one-trade/day and numeric integrity validated per symbol;
- smoke must pass before DEV;
- deterministic 20,000-rep month-block bootstrap in DEV;
- result publication uses isolated-clone `result_transport.py` only;
- workflow errors attempt automatic GitHub publication;
- DEV command has no confirmation execution path.

Static CI run `34141365544` on commit `54b42c0846508baa025cacb9c145a0dd01bd10a9` completed **SUCCESS**. It validated D053 state/manifest readiness, source identity, Python tooling and synthetic PASS/REJECT scorer regressions.

## Next operator action

Run exactly:

```powershell
git pull
py -3 .\research\runner\d053_orb30_index_run.py
```

This performs: frozen-identity preflight -> local MetaEditor compile -> 3-symbol engineering smoke -> if clean, 4-symbol 2024-2025 DEV -> frozen scoring/bootstrap -> automatic GitHub publication.

Then the user normally replies only:

`fini`

On `fini`, fetch `backtests/d053/live/latest.json` from `backtest-results` and the referenced event. Never open Jul-Aug 2026 unless the DEV event status is exactly `D053_DEV_PASS_HOLDOUT_LOCKED` and every gate is true.

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
