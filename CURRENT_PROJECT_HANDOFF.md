# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / MARKET TRANSPORT LAB V1 CLOSED / D051 NR7 INDEX CONFIRMATION READY**

## Read this first on a new chat

This file is the freshest human-readable handoff.

Then read:
1. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
2. `reports/research/MARKET_TRANSPORT_LAB_V1_CLOSEOUT_20260907.md`
3. `research/campaigns/D051_NR7_EQUITY_INDEX_CLUSTER_CONFIRMATION_V0_PREREGISTRATION_2026_09_07.md`
4. `research/runner/d051_nr7_index_confirmation.py`
5. `GUARDIAN_MASTER_MANDATE.md`
6. `GUARDIAN_STATE.json`

`GUARDIAN_STATE.json` still contains stale D044-era active fields and must be reconciled after D051 state transition. Do not let those stale active fields override this handoff or `backtest-results` evidence. Historical sections in state remain useful.

## Canonical operator UX

Preserve this exactly:

- assistant prepares GitHub, preregistration, source identity, runner changes, interpretation and next action;
- give one short PowerShell block when local MT5 execution is needed;
- runner publishes evidence automatically to `backtest-results`;
- user normally replies only **`fini`**;
- on `fini`, retrieve GitHub evidence directly;
- do not ask the user to paste logs/JSON when transport worked;
- if transport fails but local science is valid, repair publication rather than rerunning MT5;
- MT5 remains sequential.

Canonical document: `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`.

## Hard project boundaries

- Guardian Core v12.01 is the compile-validated production baseline; do not modify during research unless explicitly asked.
- Do not merge to `main` unless explicitly requested/reviewed.
- Never `git reset --hard` or destructive-clean unrelated local work.
- Legacy AutoSync v1/v2 and Guardian Backtest Bot are historical/untrusted; never fallback to them.
- Current research publication uses `research/runner/result_transport.py` isolated clones.
- No post-hoc rescue, no retuning after opened results, no relabeling seen data as OOS.

## Market Transport Lab V1 — CLOSED

Preregistration:
`research/campaigns/MARKET_TRANSPORT_LAB_V1_PREREGISTRATION_2026_09_07.md`

Closeout:
`reports/research/MARKET_TRANSPORT_LAB_V1_CLOSEOUT_20260907.md`

Frozen new universe was 12 markets:
AUDUSD, USDCAD, USDCHF, EURJPY, GBPJPY, AUDJPY, SPX500, NDX100, GER30, US30, XAGUSD, XPTUSD.

### D047 / D038 NR7 transport

- n=903
- mean=-0.0266508R/trade
- PF=0.9314
- total=-24.0657R
- 6/12 positive
- both years negative
- verdict `TRANSPORT_NO_BROAD_PASS`

Discovery only: all four equity indices were positive. Combined SPX500+NDX100+GER30+US30 = 299 trades, +31.66879718R, +0.10591571R/trade.

### D048 / D039 Inside Day transport

- n=805
- mean=-0.0400952R/trade
- PF=0.8872
- total=-32.2767R
- 3/12 positive
- verdict `TRANSPORT_NO_BROAD_PASS`

### D049 / D045 Donchian transport

Formal status: `MARKET_TRANSPORT_ENGINEERING_INCOMPLETE` because XPTUSD repeatedly ended `FINAL_INVALID_REFERENCE` while a trade was open.

XPTUSD was not silently removed. The 11 valid markets were scored descriptively only:

- n=276
- mean=-0.0198714R/trade
- PF=0.9558
- total=-5.4845R
- stress=-6.0986R
- 2024 +6.2995R
- 2025 -11.7841R
- 5/11 positive

No confirmation justified. Operationally closed; formal parent/transport verdicts unchanged.

Published descriptive event:
`backtests/d049/live/events/development/market-transport-descriptive-11-valid/20260907T134317Z`

### D050 / D040 NR4 comparator

- n=1567
- mean=-0.0499294R/trade
- PF=0.8615
- total=-78.2393R
- 4/12 positive
- verdict `COMPARATOR_NO_BROAD_PASS`

D040 remains permanently `UNCONFIRMED`.

## Current P0 — D051 NR7 equity-index cluster confirmation

D051 is a **new hypothesis**, not a rescue of D038/D047.

Preregistration:
`research/campaigns/D051_NR7_EQUITY_INDEX_CLUSTER_CONFIRMATION_V0_PREREGISTRATION_2026_09_07.md`

Runner:
`research/runner/d051_nr7_index_confirmation.py`

Frozen symbols:
- SPX500
- NDX100
- GER30
- US30

Discovery that generated the hypothesis:
D047 2024-2025 had all 4 indices positive, combined n=299, +31.66879718R, +0.10591571R/trade.

This is development/discovery only. The first untouched D051 confirmation is:

- 2026-01-02 through 2026-06-30
- Model0 / Every Tick
- unchanged NR7 strategy semantics
- same index transport spread/cost semantics as D047

Frozen H1 gates — all required:
- aggregate n >=60
- each symbol n >=10
- mean net R >0
- PF >=1.10
- >=3/4 symbols positive
- aggregate total >0
- max positive-symbol contribution share <=60%
- integrity events=0

Pass => `D051_CONFIRM_PASS_OPEN_RESERVED_HOLDOUT`.
Fail => `D051_UNCONFIRMED_CLOSE`, with no symbol removal or retuning.

Reserved final holdout already locked before H1 inspection:
2026-07-01 through 2026-08-31, same four symbols, only if H1 passes.

The D051 source is generated deterministically from the exact D047 transport derivative SHA `8718cf1ae5910577ae0c149348ad9981f8d30326ad86132b08296dd93e7f05f6`; only evidence identity/output names change. The runner publishes source identity to GitHub before MT5 execution.

CI for commit `d76c8d2b02f16a2328090ff54ab96ece252f5699` completed successfully (Guardian state consistency run 34129999008).

## Next operator action

Run exactly:

```powershell
git pull
py -3 .\research\runner\d051_nr7_index_confirmation.py
```

Then the user should normally reply only:

`fini`

On `fini`, fetch `backtests/d051/live/latest.json` from branch `backtest-results`, fetch the referenced score event, evaluate the frozen gates, and only open the reserved Jul-Aug 2026 holdout if every H1 gate passed.

## Local paths

Repo: `D:\MT5_Backtests\guardian-research`
Runner workspace: `D:\MT5_Backtests\guardian-runner`
FundedNext MT5 root: `D:\MT5_FundedNext`
MetaEditor: `D:\MT5_FundedNext\MetaEditor64.exe`
Terminal: `D:\MT5_FundedNext\terminal64.exe`
Experts: `D:\MT5_FundedNext\MQL5\Experts\GuardianResearch`
FILE_COMMON: `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\Common\Files`

## Style

Concise, direct, technically opinionated when evidence supports it. Distinguish fact, inference and unknown. Do not manufacture optimism.
