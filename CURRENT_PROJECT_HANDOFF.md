# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / MARKET TRANSPORT LAB V1 / D049 RECOVERY IN PROGRESS**

## Read this first on a new chat

This file is the freshest human-readable handoff for the current session.

Then read:
1. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
2. `GUARDIAN_MASTER_MANDATE.md`
3. `research/campaigns/MARKET_TRANSPORT_LAB_V1_PREREGISTRATION_2026_09_07.md`
4. `research/runner/market_transport_lab_v1.py`
5. `research/runner/market_transport_d049_recovery.py`
6. `GUARDIAN_STATE.json`
7. `START_HERE_NEXT_AI.md`

Important: `GUARDIAN_STATE.json` / `START_HERE_NEXT_AI.md` are currently stale from the prior D044 phase and must be regenerated/updated only after the current D049 recovery has finished and the Market Transport Lab V1 can be closed coherently. Do not let those stale D044 fields override the newer evidence in this handoff and `backtest-results`.

## Canonical operator UX — preserve this exactly

The user should operate the research stack as little as possible.

- Assistant prepares GitHub, preregistration, source identity, runner changes, state transitions and interpretation.
- Give **one short PowerShell block** whenever local MT5 execution is needed.
- Runner publishes evidence automatically to `backtest-results`.
- User normally replies only: **`fini`**.
- On `fini`, retrieve GitHub evidence directly; do not ask the user to paste logs/JSON if transport worked.
- If transport fails but valid local evidence exists, fix transport/publish evidence; do not rerun MT5 merely for transport.
- Keep MT5 sequential.

Canonical UX document: `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`.

## Scientific rules

- No post-hoc rescue/retuning after opened results.
- OOS once seen is never OOS again.
- Preregister before outcome inspection.
- Freeze source identity and costs.
- Engineering smoke before DEV.
- Confirmation only if every frozen DEV gate passes.
- Separate entry alpha from management/exit research.
- Backtest result is not live performance.
- Prefer documented, robust, multi-market mechanisms; avoid indicator soup and blind parameter search.

## Production boundary

Guardian Core **v12.01** is the frozen compile-validated production baseline. Do not modify it during this research work unless the user explicitly asks.

Do not merge to `main` unless explicitly requested/reviewed, preferably after local MT5 proof.
Never use `git reset --hard` or destructive cleanup. Preserve unrelated local/untracked work.

Legacy AutoSync v1/v2 is historical/untrusted and must never be used as fallback. The old Guardian Backtest Bot watcher was observed duplicating commits during Market Transport smoke and was intentionally stopped/removed from Startup before DEV. Current research publication is through `research/runner/result_transport.py` isolated clones.

## Recently closed experiments

- D040 NR4: DEV strong, untouched 2026 H1 failed => **UNCONFIRMED**, closed permanently.
- D045 Donchian20/10: DEV 145 trades, +0.0959087R/trade, PF 1.201, 5/6 positive; failed only frozen mean >=0.10 => **REJECT_V0**, no rounding/waiver.
- D041 / D032-M2 management: **REJECT_MANAGEMENT**; does not revoke D032 entry edge.
- D046 unconditional Deribit 08 UTC expiry screen: formal **INCONCLUSIVE_COUNT** because frozen n>=600 was unattainable; economics strongly negative, no 2026 confirmation, no post-hoc OI rescue.
- D044 Turtle Soup V0: 192 trades, -0.863R/trade, PF 0.397, 0/6 positive => **REJECT_V0**.

## Current experiment — MARKET TRANSPORT LAB V1

Purpose: test whether promising/rejected-by-threshold parent strategies transport to a preregistered **new FundedNext market universe without changing signal or management rules**.

Frozen new universe:
- AUDUSD
- USDCAD
- USDCHF
- EURJPY
- GBPJPY
- AUDJPY
- SPX500
- NDX100
- GER30
- US30
- XAGUSD
- XPTUSD

Parents / synthetic IDs:
- D038 NR7 -> D047 `D047-MARKET-TRANSPORT-NR7-V1` PRIMARY
- D039 Inside Day -> D048 `D048-MARKET-TRANSPORT-INSIDE-DAY-V1` PRIMARY
- D045 Donchian20/10 -> D049 `D049-MARKET-TRANSPORT-DONCHIAN20-10-V1` PRIMARY
- D040 NR4 -> D050 `D050-MARKET-TRANSPORT-NR4-COMPARATOR-V1` COMPARATOR only

Transport layer changes only symbol allowlist, asset-class/commission mapping and evidence identity. Frozen parent signal/management semantics remain unchanged. Parent historical verdicts remain unchanged regardless of transport results.

Smoke on AUDUSD/SPX500/XAGUSD passed for all four derivatives with clean Trade Path.

### DEV completed

D047 / NR7 transport:
- n=903
- mean=-0.0266508R/trade
- PF=0.9314
- 6/12 symbols positive
- total=-24.0657R
- 2024 and 2025 both negative
- verdict **TRANSPORT_NO_BROAD_PASS**
- notable positive totals: GBPJPY +0.37R, SPX500 +6.37R, NDX100 +8.17R, GER30 +13.43R, US30 +3.70R, XAGUSD +5.30R

D048 / Inside Day transport:
- n=805
- mean=-0.0400952R/trade
- PF=0.8872
- 3/12 symbols positive
- total=-32.2767R
- 2024 and 2025 both negative
- verdict **TRANSPORT_NO_BROAD_PASS**
- positive: USDCHF +1.62R, NDX100 +11.72R, XAGUSD +6.89R

D050 / NR4 comparator transport:
- n=1567
- mean=-0.0499294R/trade
- PF=0.8615
- 4/12 symbols positive
- total=-78.2393R
- 2024 and 2025 both negative
- verdict **COMPARATOR_NO_BROAD_PASS**
- positive: SPX500 +5.17R, NDX100 +3.35R, GER30 +15.71R, XAGUSD +12.64R

A repeated descriptive pattern is visible across already-seen results: indices, especially NDX100/GER30, and XAGUSD appear more favorable than the new Forex basket. **Do not promote/cherry-pick this observation inside V1.** It may become a separately preregistered hypothesis only after V1 is closed.

### D049 current status

The full Lab command completed D047, D048 and D050, but D049 did not publish a DEV event. `market_transport_lab_v1.py` catches one parent exception and continues, so D050 finishing did not imply 48/48 successful completion.

A dedicated recovery script was added to rerun **D049 only**:
`research/runner/market_transport_d049_recovery.py`

Current operator command already launched by the user:

```powershell
git pull
py -3 .\research\runner\market_transport_d049_recovery.py
```

In MT5 this correctly appears as generated expert `MTL_V1_D045_Donchian20_10_TickPath_M15_v1_00.ex5`; that is D049's transport derivative of parent D045, not an accidental rerun of the historical D045 experiment.

## What to do when the user says `fini`

1. Fetch `backtests/d049/live/latest.json` from branch `backtest-results`.
2. If latest is development `market-transport-score`, fetch the referenced event and extract all metrics/gates.
3. Do not ask the user to paste output.
4. Combine D047/D048/D049/D050 into a final Market Transport Lab V1 closeout.
5. Preserve parent verdicts unchanged.
6. If D049 has engineering failure/no event, diagnose the exact failure without rerunning D047/D048/D050.
7. After D049 is resolved, update/regenerate `GUARDIAN_STATE.json`, `START_HERE_NEXT_AI.md`, `CURRENT_QUEUE.json` and the next-science queue coherently.
8. Decide the next preregistered experiment from the evidence. A focused indices/XAGUSD transport hypothesis may be worth formal testing, but it must be preregistered as a **new** hypothesis and must not be presented as a V1 rescue.

## Local paths

Repo: `D:\MT5_Backtests\guardian-research`
Runner workspace: `D:\MT5_Backtests\guardian-runner`
FundedNext MT5 root: `D:\MT5_FundedNext`
MetaEditor: `D:\MT5_FundedNext\MetaEditor64.exe`
Terminal: `D:\MT5_FundedNext\terminal64.exe`
Experts destination: `D:\MT5_FundedNext\MQL5\Experts\GuardianResearch`
FILE_COMMON: `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\Common\Files`

## Tone / decision style

Be concise, direct and technically opinionated when evidence supports it. Distinguish fact, inference and unknown. Contradict the user when evidence warrants it. Do not manufacture optimism. The user wants useful scientific decisions, not reassurance or ceremony.
